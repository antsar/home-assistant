"""
Support for Avion dimmers.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.avion/
"""
import logging
import time

import voluptuous as vol

from homeassistant.const import CONF_API_KEY, CONF_DEVICES, CONF_NAME, CONF_ID
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, Light,
    PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['https://github.com/antsar/python-avion/archive/hotfix-hadebug.zip#avion==hotfix-hadebug']

_LOGGER = logging.getLogger(__name__)

SUPPORT_AVION_LED = (SUPPORT_BRIGHTNESS)

DEVICE_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default=''): cv.string,
    vol.Required(CONF_API_KEY): cv.string,
    vol.Optional(CONF_ID): cv.positive_int,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_DEVICES, default={}): {cv.string: DEVICE_SCHEMA},
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up an Avion switch."""
    lights = []
    connected_lights = {}
    for address, device_config in config[CONF_DEVICES].items():
        device = {}
        device['name'] = device_config[CONF_NAME]
        device['id'] = device_config[CONF_ID]
        device['key'] = device_config[CONF_API_KEY]
        device['address'] = address
        light = AvionLight(device, connected_lights)
        if light.is_valid:
            lights.append(light)
            connected_lights[(device['address'], device['key'])] = light

    add_devices(lights)


class AvionLight(Light):
    """Representation of an Avion light."""

    def __init__(self, device, connected_lights=[]):
        """Initialize the light."""
        # pylint: disable=import-error
        import avion
        from bluepy import btle

        self._name = device['name']
        self._address = device['address']
        self._key = device['key']
        self._id = device['id']
        self._brightness = 255
        self._state = False
        if ((self._address, self._key) in connected_lights):
            self._switch = connected_lights[(self._address, self._key)]
        else:
            self._switch = avion.avion(self._address, self._key)
            initial = time.time()
            while True:
                if time.time() - initial >= 5:
                    raise Exception('Avion failed to connect to {}.'
                                    .format(self._address))
                try:
                    self._switch.connect()
                    break
                except btle.BTLEException:
                    time.sleep(0.5)
        self.is_valid = True

    @property
    def unique_id(self):
        """Return the ID of this light."""
        return "{}.{}.{}".format(self.__class__, self._address, self._id)

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_AVION_LED

    @property
    def should_poll(self):
        """Don't poll."""
        return False

    @property
    def assumed_state(self):
        """We can't read the actual state, so assume it matches."""
        return True

    def set_state(self, brightness):
        """Set the state of this lamp to the provided brightness."""
        self._switch.set_brightness(brightness, self._id)
        return True

    def turn_on(self, **kwargs):
        """Turn the specified or all lights on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)

        if brightness is not None:
            self._brightness = brightness

        self.set_state(self.brightness)
        self._state = True

    def turn_off(self, **kwargs):
        """Turn the specified or all lights off."""
        self.set_state(0)
        self._state = False
