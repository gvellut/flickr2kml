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
  --config FILE                   Path to optional config file for the Flickr
                                  API credentials [default :
                                  /Users/guilhem/Library/Application Support/f
                                  lickr2kml/flickr_api_credentials.txt ]

  -d, --debug                     Flag to activate debug mode
  --help                          Show this message and exit.
  ```

Some notes:
- The URL of the Flickr Album must be something like `https://www.flickr.com/photos/o_0/albums/72157716704507802`
- The API keys and secrets can be obtained by registering an application with Flickr at https://www.flickr.com/services/api/misc.api_keys.html Since the API has limits on how many calls can be made per hour, I cannot share my own key.
- A config file is optional and, if present, can contain values for the `api_key` and `api_key` arguments. It should be a text file with the content like this:
```
api_key="<Flickr API Key>"
api_secret="<Flickr API Secret>"
```
(the quotes should be present)
- The default location depends on the OS (the one shown above is for my macOS machine) but can be shown with the `--help` switch. That location can be overriden with the `--config` option.
- If there is no config file, the key and secret can be passed as options on the command line or as environment variables (`FLICKR_API_KEY` and `FLICKR_API_SECRET`).
- There are 2 different formats for the description fields in the KML placemarks. I personnally generate KML for use either in Google Earth (`gearth` format) or Google My Maps (`mymaps` format). They don't present the content of the fields the same way (nor support the same features). The default is the Google Earth format.

# Example

```
flickr2kml -f https://www.flickr.com/photos/o_0/albums/72157716046011583 thiou2020.kml
```

If the API key and secret come from a config file, there is no need to pass them as argument.
