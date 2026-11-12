"""Connection setup, register snapshots and later entity selection."""

try:
    import probatio as vol
except ImportError:  # Home Assistant releases before the schema-library rename.
    import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .catalog import build_catalog
from .const import CONF_VARIABLES, DOMAIN
from .gateway import Gateway, Reading, selection_label
from .modbus import ModbusError


def connection_schema(defaults):
    return vol.Schema({
        vol.Required("name", default=defaults.get("name", "SmartLogger")): str,
        vol.Required("host", default=defaults.get("host", "")): str,
        vol.Required("port", default=defaults.get("port", 502)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required("unit_id", default=defaults.get("unit_id", 0)): vol.All(vol.Coerce(int), vol.Range(min=0, max=247)),
        vol.Required("timeout", default=defaults.get("timeout", 5)): vol.All(vol.Coerce(float), vol.Range(min=1, max=60)),
        vol.Required("retries", default=defaults.get("retries", 1)): vol.All(vol.Coerce(int), vol.Range(min=0, max=3)),
        vol.Required("request_delay", default=defaults.get("request_delay", 0.05)): vol.All(vol.Coerce(float), vol.Range(min=0, max=5)),
        vol.Required("poll_interval", default=defaults.get("poll_interval", 30)): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
        vol.Optional("devices", default=defaults.get("devices", "")): selector.TextSelector(
            selector.TextSelectorConfig(multiline=True)),
    })


def endpoint(settings):
    return f"{settings['host'].strip().lower()}:{settings['port']}:{settings['unit_id']}"


class VariableSelection:
    """Reusable progress and selection UI for setup and options."""

    _scan_task = None
    _scan_error = None
    _readings = None
    _selected = None
    _settings = None

    async def _read_catalog(self):
        gateway = None
        temporary = True
        if isinstance(self, SmartLoggerOptionsFlow):
            coordinator = getattr(self.config_entry, "runtime_data", None)
            if coordinator is not None:
                gateway = coordinator.gateway
                temporary = False
        if gateway is None:
            gateway = Gateway(self._settings)
        try:
            self._readings = await gateway.snapshot(self._catalog)
            main_readings = [r for v in self._catalog if v.group == "logger" and v.selectable
                             and (r := self._readings.get(v.key)) is not None]
            self._scan_error = None if any(r.error is None for r in main_readings) else "no_registers"
        except ModbusError:
            self._scan_error = "cannot_connect"
            self._readings = {v.key: Reading(None, v.unit, "Connection failed")
                              for v in self._catalog if v.selectable}
        finally:
            if temporary:
                await gateway.close()

    async def async_step_scan(self, user_input=None):
        starting = self._scan_task is None
        if starting:
            self._scan_task = self.hass.async_create_task(self._read_catalog())
        # Always enter progress once, even if an eager task finishes immediately.
        # Otherwise HA can forward the preceding form's input into the next step.
        if starting or not self._scan_task.done():
            return self.async_show_progress(step_id="scan", progress_action="reading_registers",
                                            progress_task=self._scan_task)
        # Propagate unexpected programmer errors rather than hiding them as network errors.
        self._scan_task.result()
        self._scan_task = None
        if self._scan_error and not isinstance(self, SmartLoggerOptionsFlow):
            next_step = "reconfigure" if self.source == "reconfigure" else "user"
        else:
            next_step = "variables"
        return self.async_show_progress_done(next_step_id=next_step)

    async def async_step_variables(self, user_input=None):
        selectable = [v for v in self._catalog if v.selectable]
        allowed = {v.key for v in selectable}
        errors = {}
        if user_input is not None:
            selection = user_input.get(CONF_VARIABLES, [])
            if not set(selection) <= allowed:
                errors["base"] = "invalid_selection"
            else:
                self._selected = selection
                if user_input.get("refresh", False):
                    return await self.async_step_scan()
                return await self._finish(selection)
        options = [{"value": v.key, "label": selection_label(v, (self._readings or {}).get(v.key))}
                   for v in selectable]
        excluded = [v for v in self._catalog if not v.selectable]
        excluded_text = "\n".join(f"- {v.name} ({v.address}, {v.datatype}, {v.unit or 'no unit'}): "
                                  f"{'write-only; no current value' if v.access == 'WO' else 'reserved'}"
                                  for v in excluded)
        return self.async_show_form(
            step_id="variables", errors=errors,
            data_schema=vol.Schema({
                vol.Required(CONF_VARIABLES, default=[k for k in (self._selected or []) if k in allowed]):
                    selector.SelectSelector(selector.SelectSelectorConfig(
                        options=options, multiple=True, mode=selector.SelectSelectorMode.LIST)),
                vol.Required("refresh", default=False): bool,
            }),
            description_placeholders={
                "count": str(len(selectable)), "excluded": excluded_text or "None",
                "scan_status": "Read completed" if not self._scan_error else
                    "Connection/read failed. Existing selections are preserved; values are unavailable.",
            },
        )


class SmartLoggerConfigFlow(VariableSelection, config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SmartLoggerOptionsFlow()

    async def async_step_user(self, user_input=None):
        return await self._connection(user_input, "user")

    async def async_step_reconfigure(self, user_input=None):
        if self._settings is None:
            self._settings = dict(self._get_reconfigure_entry().data)
        return await self._connection(user_input, "reconfigure")

    async def _connection(self, user_input, step):
        errors = {"base": self._scan_error} if self._scan_error else {}
        self._scan_error = None
        if user_input is not None:
            settings = dict(user_input)
            settings["host"] = settings["host"].strip().lower()
            settings["name"] = settings["name"].strip()
            self._settings = settings
            try:
                if not settings["host"] or not settings["name"]:
                    raise ValueError("Name and host are required")
                self._catalog = build_catalog(settings["unit_id"], settings.get("devices", ""))
            except ValueError:
                errors["base"] = "invalid_settings"
            else:
                own_id = self._get_reconfigure_entry().entry_id if step == "reconfigure" else None
                if any(e.entry_id != own_id and endpoint(dict(e.data)) == endpoint(settings)
                       for e in self._async_current_entries()):
                    errors["base"] = "already_configured"
                else:
                    await self.async_set_unique_id(endpoint(settings))
                    if step != "reconfigure":
                        self._abort_if_unique_id_configured()
                    self._selected = (list(self._get_reconfigure_entry().options.get(CONF_VARIABLES, []))
                                      if step == "reconfigure" else [])
                    return await self.async_step_scan()
        return self.async_show_form(step_id=step, data_schema=connection_schema(self._settings or {}), errors=errors)

    async def _finish(self, selection):
        if self.source == "reconfigure":
            entry = self._get_reconfigure_entry()
            # Updating data/options together triggers the entry's single reload listener.
            self.hass.config_entries.async_update_entry(
                entry, data=self._settings, options={CONF_VARIABLES: selection},
                title=self._settings["name"], unique_id=endpoint(self._settings),
            )
            return self.async_abort(reason="reconfigure_successful")
        return self.async_create_entry(title=self._settings["name"], data=self._settings,
                                       options={CONF_VARIABLES: selection})


class SmartLoggerOptionsFlow(VariableSelection, config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        self._settings = dict(self.config_entry.data)
        self._catalog = build_catalog(self._settings.get("unit_id", 0), self._settings.get("devices", ""))
        self._selected = list(self.config_entry.options.get(CONF_VARIABLES, []))
        return await self.async_step_scan()

    async def _finish(self, selection):
        return self.async_create_entry(title="", data={CONF_VARIABLES: selection})
