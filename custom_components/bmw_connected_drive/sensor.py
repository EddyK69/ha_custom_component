"""Support for reading vehicle status from BMW connected drive portal."""
import logging

from bimmer_connected.state import ChargingState
from bimmer_connected.const import (
    SERVICE_STATUS,
    SERVICE_LAST_TRIP,
    SERVICE_ALL_TRIPS,
    SERVICE_CHARGING_PROFILE,
    SERVICE_DESTINATIONS,
)

from homeassistant.const import (
    CONF_UNIT_SYSTEM_IMPERIAL,
    LENGTH_KILOMETERS,
    LENGTH_MILES,
    PERCENTAGE,
    TIME_HOURS,
    TIME_MINUTES,
    VOLUME_GALLONS,
    VOLUME_LITERS,
    ENERGY_WATT_HOUR,
    ENERGY_KILO_WATT_HOUR,
    MASS_KILOGRAMS,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level

from . import DOMAIN as BMW_DOMAIN, BMWConnectedDriveBaseEntity
from .const import CONF_ACCOUNT, DATA_ENTRIES

_LOGGER = logging.getLogger(__name__)

ATTR_TO_HA_METRIC = {
    "mileage": ["mdi:speedometer", LENGTH_KILOMETERS],
    "remaining_range_total": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "remaining_range_electric": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "remaining_range_fuel": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "max_range_electric": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "remaining_fuel": ["mdi:gas-station", VOLUME_LITERS],
    # LastTrip attributes
    "average_combined_consumption": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_electric_consumption": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_recuperation": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "electric_distance": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "saved_fuel": ["mdi:fuel", VOLUME_LITERS],
    "total_distance": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    # AllTrips attributes
    "chargecycle_range": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "total_electric_distance": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "total_saved_fuel": ["mdi:fuel", VOLUME_LITERS],
}

ATTR_TO_HA_IMPERIAL = {
    "mileage": ["mdi:speedometer", LENGTH_MILES],
    "remaining_range_total": ["mdi:map-marker-distance", LENGTH_MILES],
    "remaining_range_electric": ["mdi:map-marker-distance", LENGTH_MILES],
    "remaining_range_fuel": ["mdi:map-marker-distance", LENGTH_MILES],
    "max_range_electric": ["mdi:map-marker-distance", LENGTH_MILES],
    "remaining_fuel": ["mdi:gas-station", VOLUME_GALLONS],
    # LastTrip attributes
    "average_combined_consumption": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_electric_consumption": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_recuperation": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "electric_distance": ["mdi:map-marker-distance", LENGTH_MILES],
    "saved_fuel": ["mdi:fuel", VOLUME_GALLONS],
    "total_distance": ["mdi:map-marker-distance", LENGTH_MILES],
    # AllTrips attributes
    "chargecycle_range": ["mdi:map-marker-distance", LENGTH_MILES],
    "total_electric_distance": ["mdi:map-marker-distance", LENGTH_MILES],
    "total_saved_fuel": ["mdi:fuel", VOLUME_GALLONS],
}

ATTR_TO_HA = {
    "charging_time_remaining": ["mdi:update", TIME_HOURS],
    "charging_status": ["mdi:battery-charging", None],
    # No icon as this is dealt with directly as a special case in icon()
    "charging_level_hv": [None, PERCENTAGE],
    # LastTrip attributes
    "date": ["mdi:calendar-blank", None],
    "duration": ["mdi:timer-outline", TIME_MINUTES],
    "electric_distance_ratio": ["mdi:percent-outline", PERCENTAGE],
    # AllTrips attributes
    "battery_size_max": ["mdi:battery-charging-high", ENERGY_WATT_HOUR],
    "reset_date": ["mdi:calendar-blank", None],
    "saved_co2": ["mdi:tree-outline", MASS_KILOGRAMS],
    "saved_co2_green_energy": ["mdi:tree-outline", MASS_KILOGRAMS],
    # ChargingProfile attributes
    "is_pre_entry_climatization_enabled": ["mdi:snowflake", None],
    "preferred_charging_window": ["mdi:dock-window", None],
    "pre_entry_climatization_timer": ["mdi:av-timer", None],
    # Destination attributes
    "last_destinations": ["mdi:pin-outline", None],
}

ATTR_TO_HA_METRIC.update(ATTR_TO_HA)
ATTR_TO_HA_IMPERIAL.update(ATTR_TO_HA)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the BMW ConnectedDrive sensors from config entry."""
    if hass.config.units.name == CONF_UNIT_SYSTEM_IMPERIAL:
        attribute_info = ATTR_TO_HA_IMPERIAL
    else:
        attribute_info = ATTR_TO_HA_METRIC

    account = hass.data[BMW_DOMAIN][DATA_ENTRIES][config_entry.entry_id][CONF_ACCOUNT]
    entities = []

    for vehicle in account.account.vehicles:
        for service in vehicle.available_state_services:
            service_attr = None
            if service == SERVICE_STATUS:
                for attribute_name in vehicle.drive_train_attributes:
                    if attribute_name in vehicle.available_attributes:
                        device = BMWConnectedDriveSensor(
                            account, vehicle, attribute_name, attribute_info
                        )
                        entities.append(device)
            if service == SERVICE_LAST_TRIP:
                service_attr = vehicle.state.last_trip.available_attributes
            if service == SERVICE_ALL_TRIPS:
                service_attr = vehicle.state.all_trips.available_attributes
            if service == SERVICE_CHARGING_PROFILE:
                service_attr = vehicle.state.charging_profile.available_attributes
            if service == SERVICE_DESTINATIONS:
                service_attr = vehicle.state.last_destinations.available_attributes
            if service_attr:
                for attribute_name in service_attr:
                    device = BMWConnectedDriveSensor(
                        account, vehicle, attribute_name, attribute_info, service
                    )
                    entities.append(device)

    async_add_entities(entities, True)


class BMWConnectedDriveSensor(BMWConnectedDriveBaseEntity, Entity):
    """Representation of a BMW vehicle sensor."""

    def __init__(self, account, vehicle, attribute: str, attribute_info, service=None):
        """Initialize BMW vehicle sensor."""
        super().__init__(account, vehicle)

        self._attribute = attribute
        self._service = service
        self._state = None
        self._attribute_info = attribute_info
        if self._service:
            self._name = f"{self._vehicle.name} {self._service.lower()}_{self._attribute}"
            self._unique_id = f"{self._vehicle.vin}-{self._service.lower()}-{self._attribute}"
        else:
            self._name = f"{self._vehicle.name} {self._attribute}"
            self._unique_id = f"{self._vehicle.vin}-{self._attribute}"

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        vehicle_state = self._vehicle.state.vehicle_status
        charging_state = vehicle_state.charging_status in [ChargingState.CHARGING]

        if self._attribute == "charging_level_hv":
            return icon_for_battery_level(
                battery_level=vehicle_state.charging_level_hv, charging=charging_state
            )
        else:
            icon, _ = self._attribute_info.get(self._attribute, [None, None])
        return icon

    @property
    def state(self):
        """Return the state of the sensor.

        The return type of this call depends on the attribute that
        is configured.
        """
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Get the unit of measurement."""
        unit = self._attribute_info.get(self._attribute, [None, None])[1]
        return unit

    def update(self) -> None:
        """Read new state data from the library."""
        _LOGGER.debug("Updating %s", self._vehicle.name)
        vehicle_state = self._vehicle.state.vehicle_status
        vehicle_last_trip = self._vehicle.state.last_trip
        vehicle_all_trips = self._vehicle.state.all_trips
        vehicle_charging_profile = self._vehicle.state.charging_profile
        vehicle_last_destinations = self._vehicle.state.last_destinations
        if self._attribute == "charging_status":
            self._state = getattr(vehicle_state, self._attribute).value
        elif self.unit_of_measurement == VOLUME_GALLONS:
            value = getattr(vehicle_state, self._attribute)
            value_converted = self.hass.config.units.volume(value, VOLUME_LITERS)
            self._state = round(value_converted)
        elif self.unit_of_measurement == LENGTH_MILES:
            value = getattr(vehicle_state, self._attribute)
            value_converted = self.hass.config.units.length(value, LENGTH_KILOMETERS)
            self._state = round(value_converted)
        elif self._service is None:
            self._state = getattr(vehicle_state, self._attribute)
        elif self._service == SERVICE_LAST_TRIP:
            self._state = getattr(vehicle_last_trip, self._attribute)
        elif self._service == SERVICE_ALL_TRIPS:
            attr = getattr(vehicle_all_trips, self._attribute)
            if self._attribute in ("average_combined_consumption", "average_electric_consumption",
                "average_recuperation", "chargecycle_range"):
                self._state = attr.user_average
            elif self._attribute == "total_electric_distance":
                self._state = attr.user_total
            else:
                self._state = attr
        elif self._service == SERVICE_CHARGING_PROFILE:
            attr = getattr(vehicle_charging_profile, self._attribute)
            if self._attribute == "preferred_charging_window":
                self._state = f"{attr.start_time}-{attr.end_time}"
            elif self._attribute == "pre_entry_climatization_timer":
                self._state = len(attr)
            else:
                self._state = attr
        elif self._service == SERVICE_DESTINATIONS:
            attr = getattr(vehicle_last_destinations, self._attribute)
            if self._attribute == "last_destinations":
                self._state = len(attr)
            else:
                self._state = attr
