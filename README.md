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
  -f, --flickr_album TEXT   URL of Flickr album  [required]
  -t, --template TEXT       Choice of format for the placemark description,
                            either predefined (gearth [default], mymaps) or as
                            a path to a custom template

  -n, --name_template TEXT  Choice of format for the placemark name, as a path
                            to a custom template [default: empty]

  --api_key TEXT            Flickr API key  [required]
  --api_secret TEXT         Flickr API secret  [required]
  -p, --pushpin             Flag to make each placemark a simple pushpin
                            instead of a small image

  -a, --template_arg TEXT   Variable to pass to the template (multiple
                            possible)

  --config FILE             Path to optional config file for the Flickr API
                            credentials [default :
                            /Users/guilhem/Library/Application
                            Support/flickr2kml/flickr_api_credentials.txt]

  -d, --debug               Flag to activate debug mode
  --help                    Show this message and exit.
  ```

The URL of the Flickr album must be something like `https://www.flickr.com/photos/o_0/albums/72157716704507802`

## Name and description

There are 2 different formats for the description fields in the KML placemarks. I personnally generate KML for use either in Google Earth (`gearth` format) or Google My Maps (`mymaps` format). They don't present the content of the fields the same way (nor support the same features). The default is the Google Earth format.

By default, the KML names are left empty.

### Template

It is also possible to configure custom name and description formats by passing a path to a [Jinja2 template file](https://jinja.palletsprojects.com/en/3.0.x/templates/) with the `-t / --template` option (for the description) and the `-n / --name_template` option (for the name).

#### Description

The description template must return a HTML fragment (a simple text wthout any markup will do though). 

The 2 predefined templates can be used as a starting point:

- [`gearth`](https://github.com/gvellut/flickr2kml/blob/master/flickr2kml/template_gearth.html)
- [`mymaps`](https://github.com/gvellut/flickr2kml/blob/master/flickr2kml/template_mymaps.html)

#### Name

The name template must return a text (HTML is not supported).

A sample for the name is available here:

- [Sample](https://github.com/gvellut/flickr2kml/blob/master/sample/name_datetaken.txt)

It simply outputs a formatted `date taken`. The format specificaton is the one used by Python [from the datetime package](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes).

#### Template arguments

Besides fields obtained from the Flickr API (which change for each photo; See secton below), it is also possible to pass arguments to the template, which will stay the same for every photo. The `-a / --template_arg` option can be used multiple times for multiple arguments.

Example: 

```
-a MYARG=value -a SIZE=350
```

The `SIZE` argument, if not redefined on the command-line, is set to `500` i.e. equivalent to `-a SIZE=500`. The reason is that it is used by the predefined templates: There would be an error if not present. Custom templates are free not to use it though.

#### Fields

Here are the main fields obtained from the Flickr API:

- `id`
- `secret`
- `originalsecret`
- `originalformat`
- `title`
- `description`
- `datetaken`: Date taken in ISO format (string) as returned by the API
- `ownername`
- `pathalias`
- `views`: Number of views
- `tags`
- `latitude`
- `longitude`
- `url_sq`
- `height_sq`
- `width_sq`
- `url_t`
- `height_t`
- `width_t`
- `url_s`
- `height_s`
- `width_s`
- `url_m`
- `height_m`
- `width_m`
- `url_o`: URL of the original photo
- `height_o`
- `width_o`

Additional fields (computed by flickr2kml) are:
- `page_url`: link to the photo page on the Flickr website
- `lonlat`: Python tuple
- `img_url`: same as `url_m`
- `icon_url`: same as `url_sq`
- `orientation`: either `landscape` or `portrait`
- `datetaken_p`: Python date object obtained by parsing the datetaken from the Flickr API. There is no timezone.

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

# Examples

## Simple

```
flickr2kml -f https://www.flickr.com/photos/o_0/albums/72157716046011583 thiou2020.kml
```

If the API key and secret come from a config file, there is no need to pass them as argument.

## With templates

```
flickr2kml -f https://www.flickr.com/photos/o_0/albums/72157716046011583 thiou2020.kml
```