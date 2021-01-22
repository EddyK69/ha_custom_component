"""Support for reading vehicle status from BMW connected drive portal."""
import logging
import re

from bimmer_connected.state import ChargingState
from bimmer_connected.const import (
    SERVICE_STATUS,
    SERVICE_LAST_TRIP,
    SERVICE_ALL_TRIPS,
    SERVICE_CHARGING_PROFILE,
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
    "average_combined_consumption_community_average": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_combined_consumption_community_high": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_combined_consumption_community_low": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_combined_consumption_user_average": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_electric_consumption_community_average": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_electric_consumption_community_high": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_electric_consumption_community_low": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_electric_consumption_user_average": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_recuperation_community_average": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_recuperation_community_high": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_recuperation_community_low": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "average_recuperation_user_average": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "chargecycle_range_community_average": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "chargecycle_range_community_high": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "chargecycle_range_community_low": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "chargecycle_range_user_average": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "chargecycle_range_user_current_charge_cycle": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "chargecycle_range_user_high": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "total_electric_distance_community_average": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "total_electric_distance_community_high": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "total_electric_distance_community_low": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "total_electric_distance_user_average": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "total_electric_distance_user_total": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
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
    "average_combined_consumption_community_average": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_combined_consumption_community_high": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_combined_consumption_community_low": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_combined_consumption_user_average": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_electric_consumption_community_average": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_electric_consumption_community_high": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_electric_consumption_community_low": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_electric_consumption_user_average": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_recuperation_community_average": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_recuperation_community_high": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_recuperation_community_low": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "average_recuperation_user_average": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "chargecycle_range_community_average": ["mdi:map-marker-distance", LENGTH_MILES],
    "chargecycle_range_community_high": ["mdi:map-marker-distance", LENGTH_MILES],
    "chargecycle_range_community_low": ["mdi:map-marker-distance", LENGTH_MILES],
    "chargecycle_range_user_average": ["mdi:map-marker-distance", LENGTH_MILES],
    "chargecycle_range_user_current_charge_cycle": ["mdi:map-marker-distance", LENGTH_MILES],
    "chargecycle_range_user_high": ["mdi:map-marker-distance", LENGTH_MILES],
    "total_electric_distance_community_average": ["mdi:map-marker-distance", LENGTH_MILES],
    "total_electric_distance_community_high": ["mdi:map-marker-distance", LENGTH_MILES],
    "total_electric_distance_community_low": ["mdi:map-marker-distance", LENGTH_MILES],
    "total_electric_distance_user_average": ["mdi:map-marker-distance", LENGTH_MILES],
    "total_electric_distance_user_total": ["mdi:map-marker-distance", LENGTH_MILES],
    "total_saved_fuel": ["mdi:fuel", VOLUME_GALLONS],
}

ATTR_TO_HA_GENERIC = {
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
    "preferred_charging_window_start_time": ["mdi:dock-window", None],
    "preferred_charging_window_end_time": ["mdi:dock-window", None],
    "pre_entry_climatization_timer_1_timer_enabled": ["mdi:av-timer", None],
    "pre_entry_climatization_timer_1_departure_time": ["mdi:av-timer", None],
    "pre_entry_climatization_timer_1_weekdays": ["mdi:av-timer", None],
    "pre_entry_climatization_timer_2_timer_enabled": ["mdi:av-timer", None],
    "pre_entry_climatization_timer_2_departure_time": ["mdi:av-timer", None],
    "pre_entry_climatization_timer_2_weekdays": ["mdi:av-timer", None],
    "pre_entry_climatization_timer_3_timer_enabled": ["mdi:av-timer", None],
    "pre_entry_climatization_timer_3_departure_time": ["mdi:av-timer", None],
    "pre_entry_climatization_timer_3_weekdays": ["mdi:av-timer", None],
}

ATTR_TO_HA_METRIC.update(ATTR_TO_HA_GENERIC)
ATTR_TO_HA_IMPERIAL.update(ATTR_TO_HA_GENERIC)

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
            if service == SERVICE_STATUS:
                for attribute_name in vehicle.drive_train_attributes:
                    if attribute_name in vehicle.available_attributes:
                        device = BMWConnectedDriveSensor(
                            account, vehicle, attribute_name, attribute_info
                        )
                        entities.append(device)
            if service == SERVICE_LAST_TRIP:
                for attribute_name in vehicle.state.last_trip.available_attributes:
                    device = BMWConnectedDriveSensor(
                        account, vehicle, attribute_name, attribute_info, service
                    )
                    entities.append(device)
            if service == SERVICE_ALL_TRIPS:
                for attribute_name in vehicle.state.all_trips.available_attributes:
                    if attribute_name in ("average_combined_consumption", "average_electric_consumption",
                        "average_recuperation", "chargecycle_range", "total_electric_distance"):
                        for attr in ["community_average", "community_high", "community_low", "user_average"]:
                            device = BMWConnectedDriveSensor(
                                account, vehicle, f"{attribute_name}_{attr}", attribute_info, service
                            )
                            entities.append(device)
                        if attribute_name == "chargecycle_range":
                            for attr in ["user_current_charge_cycle", "user_high"]:
                                device = BMWConnectedDriveSensor(
                                    account, vehicle, f"{attribute_name}_{attr}", attribute_info, service
                                )
                                entities.append(device)
                        if attribute_name == "total_electric_distance":
                            for attr in ["user_total"]:
                                device = BMWConnectedDriveSensor(
                                    account, vehicle, f"{attribute_name}_{attr}", attribute_info, service
                                )
                                entities.append(device)
                    else:
                        device = BMWConnectedDriveSensor(
                            account, vehicle, attribute_name, attribute_info, service
                        )
                        entities.append(device)
            if service == SERVICE_CHARGING_PROFILE:
                for attribute_name in vehicle.state.charging_profile.available_attributes:
                    if attribute_name == "preferred_charging_window":
                        for attr in ["start_time", "end_time"]:
                            device = BMWConnectedDriveSensor(
                                account, vehicle, f"{attribute_name}_{attr}", attribute_info, service
                            )
                            entities.append(device)
                    elif attribute_name == "pre_entry_climatization_timer":
                        for timer in range(1, 4):
                            for attr in ["timer_enabled", "departure_time", "weekdays"]:
                                device = BMWConnectedDriveSensor(
                                    account, vehicle, f"{attribute_name}_{timer}_{attr}", attribute_info, service
                                )
                                entities.append(device)
                    else:
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
        if self._service:
            self._name = f"{self._vehicle.name} {self._service.lower()}_{self._attribute}"
            self._unique_id = f"{self._vehicle.vin}-{self._service.lower()}-{self._attribute}"
        else:
            self._name = f"{self._vehicle.name} {self._attribute}"
            self._unique_id = f"{self._vehicle.vin}-{self._attribute}"
        self._attribute_info = attribute_info

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
        vehicle_state = self._vehicle.state
        charging_state = vehicle_state.charging_status in [ChargingState.CHARGING]

        if self._attribute == "charging_level_hv":
            return icon_for_battery_level(
                battery_level=vehicle_state.charging_level_hv, charging=charging_state
            )
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
        vehicle_state = self._vehicle.state
        vehicle_last_trip = self._vehicle.state.last_trip
        vehicle_all_trips = self._vehicle.state.all_trips
        vehicle_charging_profile = self._vehicle.state.charging_profile
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
            for attribute in ["average_combined_consumption", "average_electric_consumption",
                "average_recuperation", "chargecycle_range", "total_electric_distance"]:
                match = re.search(f"({attribute})_(.+)", self._attribute)
                if match:
                    attr = getattr(vehicle_all_trips, match.group(1))
                    sub_attr = match.group(2)
                    self._state = getattr(attr, sub_attr)
                    return
            self._state = getattr(vehicle_all_trips, self._attribute)
        elif self._service == SERVICE_CHARGING_PROFILE:
            for attribute in ["preferred_charging_window"]:
                match = re.search(f"({attribute})_(.+)", self._attribute)
                if match:
                    attr = getattr(vehicle_charging_profile, match.group(1))
                    sub_attr = match.group(2)
                    self._state = getattr(attr, sub_attr)
                    return
            for attribute in ["pre_entry_climatization_timer"]:
                match = re.search(f"({attribute})_(\d)_(.+)", self._attribute)
                if match:
                    attr = getattr(vehicle_charging_profile, match.group(1))
                    timer_id = f"timer{match.group(2)}"
                    sub_attr = match.group(3)
                    for timer in attr:
                        if timer.value == timer_id:
                            self._state = getattr(attr[timer], sub_attr)
                            return
                    return
            self._state = getattr(vehicle_charging_profile, self._attribute)
