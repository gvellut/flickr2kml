from collections import namedtuple
import logging
import re
import sys

from addict import Dict as Addict
import click
import click_config_file
import colorama
import simplekml

from .flickr_api_auth import create_flickr_api

logger = logging.getLogger(__package__)


# specify colors for different logging levels
LOG_COLORS = {logging.ERROR: colorama.Fore.RED, logging.WARNING: colorama.Fore.YELLOW}


class ColorFormatter(logging.Formatter):
    def format(self, record, *args, **kwargs):
        if record.levelno in LOG_COLORS:
            record.msg = "{color_begin}{message}{color_end}".format(
                message=record.msg,
                color_begin=LOG_COLORS[record.levelno],
                color_end=colorama.Style.RESET_ALL,
            )
        return super().format(record, *args, **kwargs)


def setup_logging(is_debug=False):
    global logger
    if is_debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = ColorFormatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


FlickrImage = namedtuple("FlickrImage", "title page_url img_url lonlat")

FlickrAlbum = namedtuple("FlickrAlbum", "album_id url")


def write_kml(flickr_images, template_format, kml_path):
    if template_format == "mymaps":
        template = """<![CDATA[
<img src="{img_url}" width='500' />{title} {page_url}
]]>"""
    else:
        template = """<![CDATA[
<a href="{page_url}"><img src="{img_url}" width='500' /></a>
<br/><br/>{title}<br/>
]]>"""

    # TODO placemark style
    kml = simplekml.Kml()
    sharedstyle = simplekml.Style()
    sharedstyle.balloonstyle.text = "$[description]"
    for flickr_image in flickr_images:
        dvals = dict(zip(flickr_image._fields, flickr_image))
        desc = template.format(**dvals)
        pnt = kml.newpoint(description=desc, coords=[flickr_image.lonlat])
        pnt.style = sharedstyle

    kml.save(kml_path)


def parse_album_url(ctx, param, value):
    if value is not None:
        regex = r"flickr\.com/photos/[^/]+/(?:albums|sets)/(\d+)"
        m = re.search(regex, value)
        if m:
            return FlickrAlbum(m.group(1), value)
        else:
            raise click.BadParameter("Not a Flickr album URL", ctx)
    return None


def create_photopage_url(photo, user_id, album_id):
    if photo.pathalias:
        user_path = photo.pathalias
    else:
        user_path = user_id
    return f"https://www.flickr.com/photos/{user_path}/{photo.id}/in/album-{album_id}/"


def _get_page_of_photos_in_album(flickr, album_id, user_id, page, acc, output=False):
    album = Addict(
        flickr.photosets.getPhotos(
            photoset_id=album_id,
            user_id=user_id,
            extras="path_alias,url_m,geo",
            page=page,
        )
    ).photoset

    if output:
        logger.info(f"Processing album {album.title} with {album.total} photos...")

    for photo in album.photo:
        # is 0 if not georeferenced
        if photo.latitude:
            # geo
            page_url = create_photopage_url(photo, user_id, album_id)
            title = photo.title
            lonlat = [photo.longitude, photo.latitude]
            img_url = photo.url_m
            flickr_image = FlickrImage(title, page_url, img_url, lonlat)
            acc.append(flickr_image)
        # TODO add logging if not geo

    return (album.page, album.pages)


def get_photos_in_album(flickr, album_id, user_id):
    flickr_images_geo = []
    page = 1
    while True:
        _, pages = _get_page_of_photos_in_album(
            flickr,
            album_id,
            user_id,
            page,
            flickr_images_geo,
            output=(page == 1),
        )

        if page >= pages:
            break
        page += 1

    return flickr_images_geo


def flickr2kml(
    output_kml_path,
    flickr_album,
    template,
    api_key,
    api_secret,
):

    token_cache_location = click.get_app_dir("flickr2kml")
    flickr = create_flickr_api(api_key, api_secret, token_cache_location)

    user = Addict(flickr.urls.lookupUser(url=flickr_album.url))
    user_id = user.id

    flickr_images_geo = get_photos_in_album(flickr, flickr_album.album_id, user_id)

    if len(flickr_images_geo) == 0:
        logger.warning("No georeferenced image found in album!")
    write_kml(flickr_images_geo, template, output_kml_path)


CONFIG_FILE_HELP = (
    f"Path to optional config file for the Flickr API credentials [default :"
    f" {click.get_app_dir('flickr2kml')}/flickr_api_credentials.txt ]"
)


@click.command()
@click.argument(
    "output_kml_path",
    metavar="OUTPUT_KML",
    type=click.Path(writable=True, resolve_path=True, dir_okay=False),
)
@click.option(
    "-f",
    "--flickr_album",
    "flickr_album",
    help=("URL of Flickr album"),
    callback=parse_album_url,
    required=True,
)
@click.option(
    "-t",
    "--template",
    "template",
    help=("Choice of placemark description format [default: gearth]"),
    default="gearth",
    type=click.Choice(["gearth", "mymaps"]),
)
@click.option(
    "--api_key",
    "api_key",
    help=("Flickr API key"),
    envvar="FLICKR_API_KEY",
    required=True,
)
@click.option(
    "--api_secret",
    "api_secret",
    help=("Flickr API secret"),
    envvar="FLICKR_API_SECRET",
    required=True,
)
@click_config_file.configuration_option(
    "--config",
    "config_path",
    help=CONFIG_FILE_HELP,
    cmd_name="flickr2kml",
    config_file_name="flickr_api_credentials.txt",
)
@click.option(
    "-d",
    "--debug",
    "is_debug",
    is_flag=True,
    help=("Flag to activate debug mode"),
    required=False,
)
def main(**kwparams):
    """Generate a KML file for the georeferenced photos in a Flickr album"""
    is_debug = kwparams.pop("is_debug")
    setup_logging(is_debug)
    try:
        flickr2kml(**kwparams)
    except Exception as ex:
        logger.error("*** An unrecoverable error occured ***")
        lf = logger.error if not is_debug else logger.exception
        lf(str(ex))
        sys.exit(1)


if __name__ == "__main__":
    main()
