"""Sensors for explicitly selected registers."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

DEVICE_CLASSES = {
    "A": SensorDeviceClass.CURRENT, "V": SensorDeviceClass.VOLTAGE,
    "kW": SensorDeviceClass.POWER, "kvar": SensorDeviceClass.REACTIVE_POWER,
    "kVA": SensorDeviceClass.APPARENT_POWER, "kWh": SensorDeviceClass.ENERGY,
    "°C": SensorDeviceClass.TEMPERATURE, "m/s": SensorDeviceClass.WIND_SPEED,
    "W/m²": SensorDeviceClass.IRRADIANCE,
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities(SmartLoggerSensor(coordinator, entry, v) for v in coordinator.variables)


class SmartLoggerSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, variable):
        super().__init__(coordinator)
        self.variable = variable
        self._attr_unique_id = f"{entry.entry_id}:{variable.key}"
        self._attr_name = f"{variable.name} ({variable.address})"
        if variable.group == "logger":
            self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})
        else:
            identifier = f"{entry.entry_id}:{variable.group}:{variable.target}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, identifier)}, manufacturer="Huawei",
                name=f"{entry.title} {variable.group} {variable.target}",
                model=variable.group.replace("_", " "), via_device=(DOMAIN, entry.entry_id),
            )
        # The scheduling target can change between power factor and reactive power.
        # It has no fixed device or state class, avoiding incompatible statistics.
        dynamic = variable.group == "logger" and variable.address == 40742
        self._attr_device_class = None if dynamic else DEVICE_CLASSES.get(variable.unit)
        self._attr_state_class = None
        if self._attr_device_class is not None:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        # Only lifetime monotonic production counters qualify as total_increasing.
        if variable.group == "logger" and variable.address in (40560, 40562):
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif variable.group == "meter" and variable.unit == "kWh":
            self._attr_state_class = SensorStateClass.TOTAL

    @property
    def available(self):
        reading = (self.coordinator.data or {}).get(self.variable.key)
        return super().available and reading is not None and reading.error is None

    @property
    def native_value(self):
        reading = (self.coordinator.data or {}).get(self.variable.key)
        if not reading or reading.error:
            return None
        # Older supported HA versions accept var and VA, not kvar and kVA.
        if reading.unit in ("kvar", "kVA"):
            return reading.value * 1000
        return reading.value

    @property
    def native_unit_of_measurement(self):
        reading = (self.coordinator.data or {}).get(self.variable.key)
        unit = reading.unit if reading and not reading.error else self.variable.unit
        return {"kvar": "var", "kVA": "VA"}.get(unit, unit)

    @property
    def extra_state_attributes(self):
        v = self.variable
        reading = (self.coordinator.data or {}).get(v.key)
        return {
            "register_address": v.address, "modbus_unit_id": v.unit_id,
            "data_type": v.datatype, "register_count": v.count,
            "source_unit": reading.unit if reading else v.unit,
            "scale_divisor": "mode-dependent" if v.gain == 0 else v.gain,
            "access": v.access, "source_document": "Huawei Issue 37, 2020-06-24",
            "source_page": v.source_page,
            "read_error": reading.error if reading else "No reading",
        }
