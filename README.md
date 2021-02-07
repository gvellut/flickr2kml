# flickr2kml

Simple command-line tool to generate a KML from the georeferenced photos in a Flickr album

# Install

The tool requires Python 3.6+.

To install, launch :

```console
pip install flickr2kml
```

The command above will install the `flickr2kml` Python library and its dependencies. The library includes a command-line script, also named `flickr2kml`, whose functionality is described below.

# Usage

Use the `--help` flag to get an overview of the arguments:

```
~$ flickr2kml --help
Usage: flickr2kml [OPTIONS] OUTPUT_KML

  Generate a KML file for the georeferenced photos in a Flickr album

Options:
  -f, --flickr_album TEXT         URL of Flickr album  [required]
  -t, --template [gearth|mymaps]  Choice of placemark description format
                                  [default: gearth]

  --api_key TEXT                  Flickr API key  [required]
  --api_secret TEXT               Flickr API secret  [required]
  -p, --pushpin                   Flag to make each placemark a simple pushpin
                                  instead of a small image

  --config FILE                   Path to optional config file for the Flickr
                                  API credentials [default :
                                  /Users/guilhem/Library/Application Support/f
                                  lickr2kml/flickr_api_credentials.txt]

  -d, --debug                     Flag to activate debug mode
  --help                          Show this message and exit.
  ```

Some notes:
- The URL of the Flickr album must be something like `https://www.flickr.com/photos/o_0/albums/72157716704507802`
- There are 2 different formats for the description fields in the KML placemarks. I personnally generate KML for use either in Google Earth (`gearth` format) or Google My Maps (`mymaps` format). They don't present the content of the fields the same way (nor support the same features). The default is the Google Earth format.

## API permission

- The API keys and secrets can be obtained by registering a non-commercial application with Flickr at https://www.flickr.com/services/api/misc.api_keys.html Since the API has limits on how many calls can be made per hour, I cannot share my own key.
- A config file is optional and, if present, can contain values for the `api_key` and `api_secret` arguments. It should be a text file with the content like this:
```
api_key="<Flickr API Key>"
api_secret="<Flickr API Secret>"
```
(the quotes should be present)
- The default location depends on the OS (the one shown above is for my macOS machine) but can be shown with the `--help` switch. That location can be overriden with the `--config` option.
- If there is no config file, the key and secret can be passed as options on the command line or as environment variables (`FLICKR_API_KEY` and `FLICKR_API_SECRET`).

### Log in to Flickr and authorize the application

The first time the tool is run on the command-line, a token for accessing the API must be generated. It is pretty straightforward:
- A web page in the default browser will open. 
- If not logged in to Flickr, a Flickr login screen will be presented in order to log in to Flickr. 
- Then a request to grant permission to the application is made: The permission is only given for the specific API key obtained when registering yourself.
- Once pernission has been granted by the logged in user, a 9-digit code will be displayed: It needs to be copied and pasted on the command line after the prompt "Verifier code:".

After that process, an access token will be cached inside an `oauth-tokens.sqlite` file stored on the same directory as the default location of the API key config file (which can vary depending on the OS ; See above).

As long as the token is cached, there will be no need no login again for subsequent runs (that is until the token expires).

The tool will run with the permission of the user that logged in. In order to switch user, the `oauth-tokens.sqlite` will need to be deleted.

# Example

```
flickr2kml -f https://www.flickr.com/photos/o_0/albums/72157716046011583 thiou2020.kml
```

If the API key and secret come from a config file, there is no need to pass them as argument.
