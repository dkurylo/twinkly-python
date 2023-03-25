#https://xled-docs.readthedocs.io/en/latest/
import builtins
import sys
import json
import requests
import socket
import base64
import datetime
import time
import math
import random
import colorsys
import cv2
from PIL import Image

effect_duration = 15 #seconds
effect_speed = 100 #percent

mode_realtime = "rt"
frame_rate = 25 #fps; 25

color_space_rgb = "RGB"
color_space_hsv = "HSV"

ani_dir_up = "UP"
ani_dir_down = "DOWN"
ani_dir_rnd = "RND"

class Api:
    led_profile_rgb = "RGB"
    led_profile_rgbw = "RGBW"

    twinkly_udp_port = 7777

    http = "http://"
    login_uri = "/xled/v1/login"
    auth_uri = "/xled/v1/verify"
    info_uri = "/xled/v1/gestalt"
    layout_uri = "/xled/v1/led/layout/full"
    mode_uri = "/xled/v1/led/mode"

    header_content_type = "Content-Type"
    header_auth_token = "X-Auth-Token"

    header_value_application_json = "application/json"

    key_auth_token = "authentication_token"
    key_auth_token_expires_in = "authentication_token_expires_in"
    key_auth_challenge_response = "challenge-response"
    key_challenge = "challenge"
    key_code = "code"
    key_mode = "mode"

    json_key_number_of_led = "number_of_led"
    json_key_led_profile = "led_profile"
    json_key_frame_rate = "frame_rate"

    def __init__( self, twinkly_settings, twinkly_mode ):
        self.twinkly_settings = twinkly_settings
        self.twinkly_mode = twinkly_mode

        self.twinkly_auth_challenge = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
        self.twinkly_auth_key = ""
        self.twinkly_auth_key_expiration = 0
        self.twinkly_auth_key_retrieval_dt = 0

    def connect( self ):
        if not self.__api_authorise():
            return False
        if not self.__api_get_info():
            return False
        if not self.__api_get_layout():
            return False
        if not self.__api_set_mode( self.twinkly_mode ):
            return False
        return True


    def __api_response_status_ok( self, json ):
        response_status = json.get(self.key_code)
        if response_status != 1000:
            builtins.print("   Response not successful!")
            return False
        return True

    def __api_authorise( self ):
        builtins.print("Logging in")
        login_response = requests.post(
            self.http + self.twinkly_settings.twinkly_ip + self.login_uri,
            params=None,
            headers={ self.header_content_type: self.header_value_application_json },
            data="{\"" + self.key_challenge + "\": \"" + self.twinkly_auth_challenge + "=\"}",
            cookies=None,
            auth=None,
            timeout=10
        )
        login_response_json = login_response.json()
        if not self.__api_response_status_ok( login_response_json ):
            return False
        self.twinkly_auth_key = login_response_json.get(self.key_auth_token)
        self.twinkly_auth_key_expiration = login_response_json.get(self.key_auth_token_expires_in)
        self.twinkly_auth_key_retrieval_dt = datetime.datetime.now()
        twinkly_challenge_response = login_response_json.get(self.key_auth_challenge_response)
        builtins.print( "  Auth key: " + self.twinkly_auth_key )
        builtins.print( "  Expires in: " + builtins.str( self.twinkly_auth_key_expiration ) )
        if self.twinkly_auth_key is None or self.twinkly_auth_key == "" or twinkly_challenge_response is None or twinkly_challenge_response == "":
            return False

        builtins.print("")
        builtins.print("Authorising")
        auth_response = requests.post(
            self.http + self.twinkly_settings.twinkly_ip + self.auth_uri,
            params=None,
            headers={ self.header_auth_token: self.twinkly_auth_key },
            data="{\"" + self.key_auth_challenge_response + "\": \"" + twinkly_challenge_response + "\"}",
            cookies=None,
            auth=None,
            timeout=10
        )
        auth_response_json = auth_response.json()
        if not self.__api_response_status_ok( auth_response_json ):
            return False

        builtins.print("  OK")
        return True

    def __api_get_info( self ):
        builtins.print("")
        builtins.print("Getting info")
        response = requests.get(
            self.http + self.twinkly_settings.twinkly_ip + self.info_uri,
            params=None,
            headers=None,
            data=None,
            cookies=None,
            auth=None,
            timeout=10
        )
        response_json = response.json()
        if not self.__api_response_status_ok( response_json ):
            return False
        self.twinkly_settings.twinkly_led_number = response_json.get(self.json_key_number_of_led)
        builtins.print( "  No of LEDs: " + builtins.str(self.twinkly_settings.twinkly_led_number) )
        self.twinkly_settings.twinkly_led_profile = response_json.get(self.json_key_led_profile)
        builtins.print( "  LED Profile: " + self.twinkly_settings.twinkly_led_profile )
        #global twinkly_frame_rate
        #self.twinkly_settings.twinkly_frame_rate = response_json.get(json_key_frame_rate)
        #builtins.print( "  Frame Rate: " + builtins.str(self.twinkly_settings.twinkly_frame_rate) )
        if self.twinkly_settings.twinkly_led_number is None or self.twinkly_settings.twinkly_led_number == "" or self.twinkly_settings.twinkly_led_profile is None or self.twinkly_settings.twinkly_led_profile == "":
            return False

        return True

    def __api_get_layout( self ):
        builtins.print("")
        builtins.print("Getting layout")
        response = requests.get(
            self.http + self.twinkly_settings.twinkly_ip + self.layout_uri,
            params=None,
            headers={ self.header_auth_token: self.twinkly_auth_key },
            data=None,
            cookies=None,
            auth=None,
            timeout=10
        )
        response_json = response.json()
        if not self.__api_response_status_ok( response_json ):
            return False
        self.twinkly_settings.twinkly_led_layout = response_json.get("coordinates") #x: -1..1; y: 0..1

        builtins.print("  OK")
        return True

    def __api_set_mode( self, twinkly_mode ):
        builtins.print("")
        builtins.print("Setting realtime mode")
        response = requests.post(
            self.http + self.twinkly_settings.twinkly_ip + self.mode_uri,
            params=None,
            headers={ self.header_content_type: self.header_value_application_json,
                      self.header_auth_token: self.twinkly_auth_key },
            data="{\"" + self.key_mode + "\": \"" + twinkly_mode + "\"}",
            cookies=None,
            auth=None,
            timeout=1
        )
        response_json = response.json()
        if not self.__api_response_status_ok( response_json ):
            return False

        builtins.print("  OK")
        return True

    def send_frame( self, leds ):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        frame_fragment_number = 0
        current_frame_header = self.__get_frame_header( frame_fragment_number )
        current_frame = b''

        for current_led_index in builtins.range(builtins.len(leds)):
            current_led = leds[current_led_index]
            current_led_value = b''
            if self.twinkly_settings.twinkly_led_profile == self.led_profile_rgbw:
                current_led_value += current_led[3].to_bytes(1, "big")
            current_led_value += current_led[0].to_bytes(1, "big") + current_led[1].to_bytes(1, "big") + current_led[2].to_bytes(1, "big")
            current_frame += current_led_value

            if ( current_led_index == builtins.len(leds) - 1 ) or ( self.twinkly_settings.twinkly_led_profile == self.led_profile_rgb and builtins.len(current_frame) + 3 > 900 ) or ( self.twinkly_settings.twinkly_led_profile == self.led_profile_rgbw and builtins.len(current_frame) + 4 > 900 ):
                sock.sendto( current_frame_header + current_frame, ( self.twinkly_settings.twinkly_ip, self.twinkly_udp_port ) )
                frame_fragment_number += 1
                current_frame_header = self.__get_frame_header( frame_fragment_number )
                current_frame = b''

    def __get_frame_header( self, frame_fragment_number ):
        decoded_auth_token = base64.b64decode(self.twinkly_auth_key)
        frame_header = b'\x03'
        frame_header += decoded_auth_token
        frame_header += b'\x00\x00'
        frame_header += frame_fragment_number.to_bytes(1, "big")
        return frame_header

class TwinklySetting:
    def __init__( self, twinkly_ip, twinkly_has_two_strings=True, twinkly_first_and_second_winding_switched=True, twinkly_use_transition=False, twinkly_effects=[] ):
        self.twinkly_ip = twinkly_ip
        self.twinkly_has_two_strings = twinkly_has_two_strings #whether twinkly has two separate strings coming out from controller
        self.twinkly_first_and_second_winding_switched = twinkly_first_and_second_winding_switched #whether the first string continues after the second one ends physically on a tree; needed for linear effects
        self.twinkly_use_transition = twinkly_use_transition #whether transition effects are used
        self.twinkly_effects = twinkly_effects

        self.twinkly_led_number = 0
        self.twinkly_led_profile = ""
        self.twinkly_led_layout = []

class TwinklyProcessor:
    def __init__( self, twinkly_settings, twinkly_mode ):
        self.twinkly_settings = twinkly_settings
        self.twinkly_mode = twinkly_mode

        self.api = Api( self.twinkly_settings, self.twinkly_mode )

        self.current_effect = None
        self.current_effect_mask = None
        self.current_effect_index = None
        self.current_effect_start_time = None

        self.next_effect = None
        self.next_effect_mask = None

        self.effect_transition = None

        self.next_frame_rendered_leds = None

    def init( self ):
        if not self.api.connect():
            return False
        self.effect_transition = TwinklyEffectTransition( self.twinkly_settings )
        return True

    def play_effect( self ):
        if self.next_frame_rendered_leds is None:
            self.next_frame_rendered_leds = self.__generate_next_frame()
        self.api.send_frame( self.next_frame_rendered_leds )
        self.next_frame_rendered_leds = self.__generate_next_frame()

    def __generate_next_frame( self ):
        if self.current_effect_start_time is None or (datetime.datetime.now() - self.current_effect_start_time).total_seconds() >= effect_duration:
            self.__init_new_effect()
            self.current_effect_start_time = datetime.datetime.now()
        else:
            self.current_effect.tick()
            if self.next_effect is not None:
                self.next_effect.tick()
            if self.current_effect_mask is not None:
                self.current_effect_mask.tick()
            if self.next_effect_mask is not None:
                self.next_effect_mask.tick()

        if self.next_effect is not None and self.effect_transition.is_complete():
            self.current_effect = self.next_effect
            self.next_effect = None
            self.current_effect_mask = self.next_effect_mask
            self.next_effect_mask = None

        next_frame_rendered_leds = self.current_effect.twinkly_string.get_leds( None, self.current_effect_mask.twinkly_string.get_leds() if self.current_effect_mask is not None else None )
        if self.next_effect is not None and not self.effect_transition.is_complete():
            self.effect_transition.tick()
            next_effect_rendered_leds = self.next_effect.twinkly_string.get_leds( None, self.next_effect_mask.twinkly_string.get_leds() if self.next_effect_mask is not None else None )
            next_frame_rendered_leds = self.effect_transition.get_leds( next_frame_rendered_leds, next_effect_rendered_leds )
        return next_frame_rendered_leds

    def __init_new_effect( self ):
        self.current_effect_index = self.__get_new_effect_index()
        effect_to_init = self.twinkly_settings.twinkly_effects[ self.current_effect_index ]
        if self.twinkly_settings.twinkly_use_transition and self.current_effect is not None:
            self.effect_transition.init()
            self.next_effect = self.__get_effect( effect_to_init )
            self.next_effect_mask = self.__get_effect_mask( effect_to_init )
        else:
            self.current_effect = self.__get_effect( effect_to_init )
            self.current_effect_mask = self.__get_effect_mask( effect_to_init )

    def __get_effect( self, effect_to_init ):
        return builtins.getattr( sys.modules[__name__], effect_to_init.get_effect_name() )( TwinklyString( self.twinkly_settings ), effect_to_init.get_effect_params() )

    def __get_effect_mask( self, effect_to_init ):
        effect_mask = None
        if effect_to_init.get_mask_name() is not None:
            effect_mask = builtins.getattr( sys.modules[__name__], effect_to_init.get_mask_name() )( TwinklyString( self.twinkly_settings ), effect_to_init.get_mask_params() )
        return effect_mask

    def __get_new_effect_index( self ):
        new_effect_index = None
        while new_effect_index is None or (self.current_effect_index == new_effect_index and builtins.len(self.twinkly_settings.twinkly_effects) > 1):
            new_effect_index = random.randint( 0, builtins.len(self.twinkly_settings.twinkly_effects) - 1 )
        return new_effect_index

class TwinklyString:
    def __init__( self, twinkly_settings ):
        self.twinkly_settings = twinkly_settings
        self.leds = []

    def init_leds( self ):
        self.leds = self.init_new_leds()

    def init_new_leds( self ):
        leds = []
        for current_led_index in builtins.range( self.twinkly_settings.twinkly_led_number ):
            leds.append( [ 0, 0, 0, 0 ] )
        return leds

    def convert_color_rgb_to_hsv( self, led ):
        hsv = colorsys.rgb_to_hsv( led[0] / 255.0, led[1] / 255.0, led[2] / 255.0 )
        led[0] = builtins.int( hsv[0] * 360 )
        led[1] = builtins.int( hsv[1] * 100 )
        led[2] = builtins.int( hsv[2] * 100 )
        return led

    def convert_color_hsv_to_rgb( self, led ):
        rgb = colorsys.hsv_to_rgb( led[0] / 360.0, led[1] / 100.0, led[2] / 100.0 )
        led[0] = builtins.int( 255 * rgb[0] )
        led[1] = builtins.int( 255 * rgb[1] )
        led[2] = builtins.int( 255 * rgb[2] )
        return led

    def get_leds( self, leds=None, mask_leds=None ):
        if leds is None:
            leds = self.leds
        if mask_leds is None:
            return leds
        else:
            masked_leds = []
            for current_led_index in builtins.range(builtins.len(leds)):
                current_led_color = leds[current_led_index]
                mask_led_color = mask_leds[current_led_index]
                masked_current_led_color_r = 0 if mask_led_color[0] == 0 else ( current_led_color[0] if mask_led_color[0] == 255 else math.ceil( current_led_color[0] * mask_led_color[0] / 255.0 ) )
                masked_current_led_color_g = 0 if mask_led_color[1] == 0 else ( current_led_color[1] if mask_led_color[1] == 255 else math.ceil( current_led_color[1] * mask_led_color[1] / 255.0 ) )
                masked_current_led_color_b = 0 if mask_led_color[2] == 0 else ( current_led_color[2] if mask_led_color[2] == 255 else math.ceil( current_led_color[2] * mask_led_color[2] / 255.0 ) )
                masked_current_led_color_w = 0 if mask_led_color[3] == 0 else ( current_led_color[3] if mask_led_color[3] == 255 else math.ceil( current_led_color[3] * mask_led_color[3] / 255.0 ) )
                masked_leds.append( [ masked_current_led_color_r, masked_current_led_color_g, masked_current_led_color_b, masked_current_led_color_w ] )
            return masked_leds

    def set_leds( self, leds ):
        self.leds = leds

    def get_led_at_index( self, led_index, leds=None ):
        if leds is None:
            leds = self.leds
        if self.twinkly_settings.twinkly_has_two_strings:
            if self.twinkly_settings.twinkly_first_and_second_winding_switched:
                half_twinkly_string = builtins.int( self.twinkly_settings.twinkly_led_number / 2 )
                if led_index >= half_twinkly_string:
                    return leds[led_index - half_twinkly_string]
                else:
                    return leds[led_index + half_twinkly_string]
            else:
                return leds[led_index]
        else:
            return leds[led_index]


class TwinklyEffectTransition:
    def __init__( self, twinkly_settings ):
        self.twinkly_settings = twinkly_settings
        self.twinkly_string = TwinklyString( self.twinkly_settings )
        self.twinkly_string.init_leds()
        self.transition_time_length = 3
        self.transition_step = math.ceil( builtins.len(self.twinkly_string.leds) / frame_rate / self.transition_time_length )
        self.transition_length = self.transition_step * 4
        self.transition_position = None

    def init( self ):
        self.transition_position = -1

    def tick( self ):
        self.transition_position += self.transition_step

    def is_complete( self ):
        return self.transition_position is None or self.transition_position > builtins.len(self.twinkly_string.leds) - 1 + self.transition_length

    def get_leds( self, current_effect_leds, next_effect_leds ):
        if self.transition_position < 0:
            return current_effect_leds
        if self.is_complete():
            return next_effect_leds

        for led_index in builtins.range(builtins.len(self.twinkly_string.leds)):
            led = self.twinkly_string.get_led_at_index( led_index )
            effect_led = None
            if led_index <= self.transition_position:
                effect_led = self.twinkly_string.get_led_at_index( led_index, next_effect_leds )
            elif self.transition_position < builtins.len(self.twinkly_string.leds) and led_index > self.transition_position:
                effect_led = self.twinkly_string.get_led_at_index( led_index, current_effect_leds )
            if effect_led is not None:
                led[0] = effect_led[0]
                led[1] = effect_led[1]
                led[2] = effect_led[2]
                led[3] = effect_led[3]

        for transition_led_index in builtins.range(self.transition_length):
            led_index = self.transition_position - transition_led_index
            if led_index < 0 or led_index > builtins.len(self.twinkly_string.leds) - 1:
                continue
            led = self.twinkly_string.convert_color_rgb_to_hsv( self.twinkly_string.get_led_at_index( led_index ) )
            koeff = 1 - transition_led_index / builtins.float(self.transition_length) #will have 1.0 value at start and 0.0 at the end
            #led_colors[1] = 0
            #led_colors[2] = 100
            led[1] = math.ceil( led[1] - led[1] * koeff )
            led[2] = math.ceil( led[2] + ( 100 - led[2] ) * koeff )
            self.twinkly_string.convert_color_hsv_to_rgb( led )
        return self.twinkly_string.get_leds()

#effect definitions library
#EffectRainbow params: [ number_of_rainbows 1..inf, saturation 0..100, direction "UP"/"DOWN"/"RND" ]
class EffectRainbow:
    def __init__( self, twinkly_string, params=[] ):
        self.twinkly_string = twinkly_string
        self.twinkly_string.init_leds()

        number_of_rainbows = params[0] if builtins.len(params) >= 1 and params[0] is not None and params[0] > 0 else 2
        saturation = params[1] if builtins.len(params) >= 2 and params[1] is not None and 0 <= params[1] <= 100 else 100
        self.direction = params[2] if builtins.len(params) >= 3 and ( params[2] == ani_dir_down or params[2] == ani_dir_up ) else ( ani_dir_down if random.randint( 0, 1 ) > 0 else ani_dir_up )
        speed_variation = random.randint(75, 125) / 100
        self.speed = effect_speed * speed_variation * self.twinkly_string.twinkly_settings.twinkly_led_number / 10000

        builtins.print( "Playing 'Rainbow' | Count " + builtins.str(number_of_rainbows) + (" " if number_of_rainbows < 10 else "") + " | Spd " + "{:.2f}".format(speed_variation) + " | Sat " + "{:.2f}".format(saturation/100) + " | Dir " + ("UP  " if self.direction == -1 else "DOWN") )

        hue_step = 360 * number_of_rainbows / self.twinkly_string.twinkly_settings.twinkly_led_number
        hue = 0.0

        for led_index in builtins.range(builtins.len(self.twinkly_string.leds)):
            led = self.twinkly_string.get_led_at_index( led_index )
            led[0] = hue % 360.0
            led[1] = saturation
            led[2] = 100
            twinkly_string.convert_color_hsv_to_rgb( led )
            hue += hue_step
        self.hue_step = ( 1 if self.direction == ani_dir_down else -1 ) * hue_step / number_of_rainbows * self.speed

    def tick( self ):
        for led_index in builtins.range(builtins.len(self.twinkly_string.leds)):
            led = self.twinkly_string.convert_color_rgb_to_hsv( self.twinkly_string.get_led_at_index( led_index ) )
            led[0] = ( led[0] + self.hue_step ) % 360.0
            self.twinkly_string.convert_color_hsv_to_rgb( led )

#EffectGifAnimator params: [ "filename.gif", show_animation_frame_this_number_of_times 1..inf, direction "UP"/"DOWN"/"RND" ]
class EffectGifAnimator:
    def __init__( self, twinkly_string, params=[] ):
        self.twinkly_string = twinkly_string
        self.twinkly_string.init_leds()

        self.file_name = params[0] if builtins.len(params) >= 1 and params[0] is not None and params[0] != "" else None
        if self.file_name is None:
            return
        self.ani_frame_show_times = params[1] if builtins.len(params) >= 2 and params[1] is not None and params[1] >= 0 else 1
        self.direction = params[2] if builtins.len(params) >= 3 and ( params[2] == ani_dir_down or params[2] == ani_dir_up ) else ( ani_dir_down if random.randint( 0, 1 ) > 0 else ani_dir_up )
        self.ani_frames = []
        self.ani_frame_current_index = 0
        self.ani_frame_shown_times = 0

        builtins.print( "Playing 'Gif' | " + builtins.str(self.file_name) + " | Spd " + "{:.2f}".format(1 / self.ani_frame_show_times) + "x | Dir " + ("UP  " if self.direction == ani_dir_up else "DOWN") )

        gif = cv2.VideoCapture( self.file_name )
        while True:
            next_gif_frame_exists,gif_frame_reference = gif.read() # ret=True if it finds a frame else False
            if not next_gif_frame_exists:
                break
            gif_frame_image = Image.fromarray(gif_frame_reference)
            gif_frame_image = gif_frame_image.convert("RGB")
            self.gif_width, self.gif_height = gif_frame_image.size
            gif_frame = gif_frame_image.load()

            ani_frame = []
            for gif_y in builtins.range( self.gif_height ):
                ani_line_pixel = []
                for gif_x in builtins.range( self.gif_width ):
                    gif_frame_pixel = gif_frame[gif_x, self.gif_height - 1 - gif_y]
                    ani_line_pixel.append(gif_frame_pixel)
                ani_frame.append(ani_line_pixel)

            frame_leds = self.twinkly_string.get_leds( self.twinkly_string.init_new_leds() )
            for current_led_index in builtins.range(builtins.len(frame_leds)):
                led_coordinates = self.twinkly_string.twinkly_settings.twinkly_led_layout[current_led_index]
                led_x = ( led_coordinates.get("x") + 1 ) / builtins.float(2) #convert to 0..1
                led_x = math.floor(led_x * self.gif_width)
                if led_x >= self.gif_width:
                    led_x = self.gif_width - 1
                led_y = builtins.float(led_coordinates.get("y")) #0..1
                led_y = math.floor(led_y * self.gif_height)
                if led_y >= self.gif_height:
                    led_y = self.gif_height - 1
                led_color_b,led_color_g,led_color_r = ani_frame[led_y][led_x]
                current_led = frame_leds[current_led_index]
                current_led[0] = led_color_r
                current_led[1] = led_color_g
                current_led[2] = led_color_b
            self.ani_frames.append(frame_leds)
        self.tick()

    def tick( self ):
        ani_frame = self.ani_frames[ self.ani_frame_current_index ] if self.direction == ani_dir_down else self.ani_frames[ builtins.len(self.ani_frames) - 1 - self.ani_frame_current_index]
        self.twinkly_string.set_leds( ani_frame )

        self.ani_frame_shown_times += 1
        if self.ani_frame_shown_times >= self.ani_frame_show_times:
            self.ani_frame_shown_times = 0
            self.ani_frame_current_index += 1
            if self.ani_frame_current_index == builtins.len(self.ani_frames):
                self.ani_frame_current_index = 0

class TwinklyPlayer:
    def __init__( self, twinkly_settings ):
        self.twinkly_processors = []
        for twinkly_setting in twinkly_settings:
            self.twinkly_processors.append( TwinklyProcessor( twinkly_setting, mode_realtime ) )

    def init( self ):
        twinkly_processors_successful_init = []
        for twinkly_state in self.twinkly_processors:
            if twinkly_state.init():
                twinkly_processors_successful_init.append( twinkly_state )
        self.twinkly_processors = twinkly_processors_successful_init

    def start( self ):
        builtins.print("")
        while True:
            frame_start = datetime.datetime.now()
            for twinkly_state in self.twinkly_processors:
                twinkly_state.play_effect()
            frame_end = datetime.datetime.now()
            time_used = builtins.max( builtins.float(1 / frame_rate) - ( frame_end - frame_start ).total_seconds(), 0 )
            if time_used > 0:
                time.sleep( time_used )

class TwinklyEffect:
    def __init__( self, effect_name, effect_params, mask_name=None, mask_params=None ):
        self.effect_name = effect_name
        self.effect_params = effect_params
        self.mask_name = mask_name
        self.mask_params = mask_params

    def get_effect_name(self):
        return self.effect_name

    def get_effect_params( self ):
        return self.effect_params

    def get_mask_name( self ):
        return self.mask_name

    def get_mask_params( self ):
        return self.mask_params

#effect registry
#ffmpeg -i "concat:06.gif|06.gif" 06_1.gif
#ffmpeg -i 10.gif -vf "minterpolate,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -r 30 10_2.gif
twinkly_effects_repository = [
    TwinklyEffect( "EffectRainbow", [  0.1, 100, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [  0.5, 100, ani_dir_rnd ], "EffectGifAnimator", [ "_mask/02.gif", 2, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [  1.0, 100, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [  1.0, 100, ani_dir_rnd ], "EffectGifAnimator", [ "_mask/01.gif", 2, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [  1.0,  90, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [  2.0, 100, ani_dir_rnd ], "EffectGifAnimator", [ "_mask/00.gif", 3, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [  2.0,  80, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [  4.0, 100, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [  4.0,  75, ani_dir_rnd ], "EffectGifAnimator", [ "_mask/00.gif", 3, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [  8.0, 100, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [  8.0,  75, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [ 16.0, 100, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [ 32.0, 100, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [ 64.0, 100, ani_dir_rnd ] ),
    TwinklyEffect( "EffectRainbow", [ 64.0,  80, ani_dir_rnd ], "EffectGifAnimator", [ "_mask/02.gif", 2, ani_dir_rnd ] ),
    TwinklyEffect( "EffectGifAnimator", [ "_anim/00.gif", 2, ani_dir_rnd ] ),
    TwinklyEffect( "EffectGifAnimator", [ "_anim/01.gif", 1, ani_dir_rnd ] ),
    TwinklyEffect( "EffectGifAnimator", [ "_anim/02.gif", 3, ani_dir_rnd ] ),
    TwinklyEffect( "EffectGifAnimator", [ "_anim/03.gif", 2, ani_dir_rnd ] ),
    TwinklyEffect( "EffectGifAnimator", [ "_anim/05.gif", 1, ani_dir_rnd ] ),
    TwinklyEffect( "EffectGifAnimator", [ "_anim/06.gif", 1, ani_dir_rnd ] ),
    TwinklyEffect( "EffectGifAnimator", [ "_anim/07.gif", 1, ani_dir_rnd ] ),
    TwinklyEffect( "EffectGifAnimator", [ "_anim/08.gif", 1, ani_dir_rnd ] ),
    TwinklyEffect( "EffectGifAnimator", [ "_anim/09.gif", 2, ani_dir_rnd ] ),
]

def main( player_instance=None ):
    if player_instance is None:
        player_instance = TwinklyPlayer(
            [
                TwinklySetting( "192.168.1.208", True, True, True, twinkly_effects_repository ),
                TwinklySetting( "192.168.1.218", True, True, True, twinkly_effects_repository )
                //TwinklySetting( "192.168.1.218", True, False, True, twinkly_effects_repository )
            ]
        )
    player_instance.init()
    player_instance.start()

if __name__ == "__main__":
    main()