# Requirements

`$ pip3 install beautifulsoup4 html5lib`

# Usage

```
usage: cinews [-h] {youtube,bitchute} ...

Fetch newest videos from web.

optional arguments:
  -h, --help          show this help message and exit

modules:
  {youtube,bitchute}  Run video module
    youtube           Fetches from youtube.
    bitchute          Fetches from bitchute.
```

# Modules
## YouTube

```
usage: cinews youtube [-h] (-u USER_ID | -c CHANNEL_ID)

optional arguments:
  -h, --help            show this help message and exit
  -u USER_ID, --user-id USER_ID
                        Youtube user id
  -c CHANNEL_ID, --channel-id CHANNEL_ID
                        Youtube channel id
```

## Bitchute

```
usage: cinews bitchute [-h] -c CHANNEL_ID

optional arguments:
  -h, --help            show this help message and exit
  -c CHANNEL_ID, --channel-id CHANNEL_ID
                        Bitchute channel id
```
