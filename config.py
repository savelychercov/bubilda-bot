import os
from dotenv import load_dotenv
load_dotenv()

testing = True
auto_sync_slash_commands = False
send_is_ready_message = True

id_to_send_ready_message = 550950524401483788

if testing:
    token = os.getenv("DEBUG_DISCORD_TOKEN")
    prefix = "t."
else:
    token = os.getenv("DISCORD_TOKEN")
    prefix = "b."

openai_apikey = os.getenv("OPENAI_TOKEN")
pexels_apikey = os.getenv("PEXELS_TOKEN")
tenor_apikey = os.getenv("TENOR_TOKEN")
telegram_apikey = os.getenv("TELEGRAM_TOKEN")

main_emoji = ":zipper_mouth:"

last_traceback = ""

# Events
update_event_time = 60*3  # seconds
delete_event_time = 60*60  # seconds
min_send_time = 6  # hours
max_send_time = 9  # hours
random_minutes = 59  # minutes
sell_item_on_event_chance = 0.35
send_thing_chance = 0.5
pisi_cog_logging = False
sell_min_price = 5000
sell_max_price = 9000

# Fishing
nibble_chance = 0.2
catch_thing_chance = 0.2
fish_price_aberration = 0.4
fish_fall_off_chance = 0.1

measure = {
    1: "см", 
    100: "м",
    100_000: "км",
    637_814_000: "рад. Земли",
    38_440_100_000: "Лун. раст.",
    14_959_787_070_000: "астр. ед",
    946_073_047_258_080_000: "св. год",
    3_085_677_581_491_367_279: "парсек"
    }


guild_roles = {

    1050725563117084732: { #Bubilding
        1:   1217483851220127865,
        10:  1217483972980768868,
        100:  1217484007751684137,
        1000: 1217484042379727030,
        10000: 1217484077297438720},

    1027512638164434974: { #Cherpaki
        1: 1106319930963546183,
        10:  1104787810109636629,
        100:  1105147427545153597,
        1000: 1217831992503308378,
        10000: 1217832178524881027,
        100000: 1105148312019017819}
}

admin_ids = [
    550950524401483788,  # Спавелук
    536229144355274763,  # Влии
]

loaded_cogs = []

start_balance = 0
coinflip_commission = 10
coinflip_timeout_time = 60


# Keys for memory files
keys_key = "keys"
marry_key = "marriages"
balance_key = "balance"
daily_key = "daily"
coinflip_key = "coinflip"
dates_key = "dates"
pisi_key = "pisi"
inventory_key = "inv"
shop_key = "shop"


emoji_add_chance = 0.05
emoji_enabled_guilds = [1050725563117084732]
