from collections import namedtuple
import logging
import re
import sys

from addict import Dict as Addict
import click
import click_config_file
import colorama
import dateutil.parser
import importlib_resources
from jinja2 import Template
import simplekml

from .flickr_api_auth import create_flickr_api

logger = logging.getLogger(__package__)


class InvalidTemplateArgumentError(Exception):
    pass


class TemplateError(Exception):
    pass


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


ORIENTATION_HORIZONTAL = "landscape"
ORIENTATION_VERTICAL = "portrait"


FlickrAlbum = namedtuple("FlickrAlbum", "album_id url")


def _parse_template_args(template_args):
    errors = []
    parsed = {}
    for arg in template_args:
        key_val = arg.split("=", 1)
        if len(key_val) != 2:
            errors.append(f"'{arg}'")
            continue
        key, val = key_val
        key = key.strip()
        logger.debug(f"Arg : '{key}' => '{val}'")
        parsed[key] = val

    if errors:
        errors = ",".join(errors)
        raise InvalidTemplateArgumentError(
            f"There were invalid template arguments: {errors}"
        )

    return parsed


def _read_template(template_path):
    try:
        with open(template_path, encoding="utf-8") as fp:
            template_text = fp.read()
    except Exception:
        raise TemplateError(f"Template path '{template_path}' could not be opened!")

    return template_text


def _render_image(
    kml,
    flickr_image,
    j_template,
    j_name_template,
    template_args,
    is_pushpin,
    sharedstyle,
):
    # flickr_image already a dict. No copy: won't need it after this
    dvals = flickr_image
    dvals.update(template_args)

    try:
        desc = j_template.render(**dvals)
    except Exception:
        logger.debug(dvals)
        raise TemplateError("Unable to render description template")
    desc = f"<![CDATA[{desc}]]>"

    if j_name_template:
        try:
            name = j_name_template.render(**dvals)
        except Exception:
            logger.debug(dvals)
            raise TemplateError("Unable to render name template")
        # name is not html so no cdata
    else:
        name = None

    pnt = kml.newpoint(name=name, description=desc, coords=[flickr_image.lonlat])

    if is_pushpin:
        pnt.style = sharedstyle
    else:
        _set_balloonstyle(pnt.style)
        pnt.style.iconstyle.icon.href = flickr_image.icon_url


def write_kml(
    flickr_images, template, name_template, is_pushpin, template_args, kml_path
):
    logger.debug(f"template={template} name_template={name_template}")

    if template == "mymaps":
        template_text = importlib_resources.read_text(
            __package__, "template_mymaps.html"
        )
    elif template == "gearth":
        template_text = importlib_resources.read_text(
            __package__, "template_gearth.html"
        )
    else:
        # template is considered to be a path
        template_text = _read_template(template)

    try:
        j_template = Template(template_text, autoescape=True)
    except Exception:
        raise TemplateError("Unable to parse description template")

    if name_template:
        name_template_text = _read_template(name_template)
        try:
            # not HTML so no autoescape
            j_name_template = Template(name_template_text, autoescape=False)
        except Exception:
            raise TemplateError("Unable to parse name template")
    else:
        j_name_template = None

    template_args = _parse_template_args(template_args)
    # Default size : used in gearth and mymaps templates
    if "SIZE" not in template_args:
        template_args["SIZE"] = "500"

    kml = simplekml.Kml()

    sharedstyle = None
    if is_pushpin:
        sharedstyle = simplekml.Style()
        _set_balloonstyle(sharedstyle)

    for flickr_image in flickr_images:
        _render_image(
            kml,
            flickr_image,
            j_template,
            j_name_template,
            template_args,
            is_pushpin,
            sharedstyle,
        )

    kml.save(kml_path)


def _set_balloonstyle(style):
    style.balloonstyle.text = "$[description]"


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


def _get_page_of_geo_images_in_album(
    flickr, album_id, user_id, page, acc, output=False
):
    # description in extras: Not documented in the API doc but works
    album = Addict(
        flickr.photosets.getPhotos(
            photoset_id=album_id,
            extras="license, date_upload, date_taken, owner_name, "
            "original_format, geo, tags, views, path_alias, url_sq, url_t"
            "url_s, url_m, url_l, url_h, url_k, url_3k, url_o, description",
            page=page,
        )
    ).photoset

    if output:
        logger.info(f"Processing album '{album.title}' with {album.total} photos...")

    for photo in album.photo:
        # is 0 if not georeferenced
        if photo.latitude:
            # add computed fields
            photo.page_url = create_photopage_url(photo, user_id, album_id)
            photo.lonlat = [photo.longitude, photo.latitude]
            photo.img_url = photo.url_m
            photo.icon_url = photo.url_sq
            if photo.height_m > photo.width_m:
                photo.orientation = ORIENTATION_VERTICAL
            else:
                photo.orientation = ORIENTATION_HORIZONTAL
            # description already defined on photo object but make it simpler
            photo.description = photo.description._content.strip()

            # parse the date taken so can be formatted in template
            photo.datetaken_p = dateutil.parser.isoparse(photo.datetaken)

            acc.append(photo)

    # return album for data about it
    return album


def get_geo_images_in_album(flickr, album_id, user_id):
    flickr_images_geo = []
    page = 1
    while True:
        album = _get_page_of_geo_images_in_album(
            flickr,
            album_id,
            user_id,
            page,
            flickr_images_geo,
            output=(page == 1),
        )

        if page >= album.pages:
            break
        page += 1

    if album and len(flickr_images_geo) < album.total:
        diff = album.total - len(flickr_images_geo)
        logger.warning(f"{diff} images in the album are not georeferenced")

    return flickr_images_geo


def flickr2kml(
    output_kml_path,
    flickr_album,
    template,
    name_template,
    api_key,
    api_secret,
    is_pushpin,
    template_args,
):
    token_cache_location = click.get_app_dir(DEFAULT_APP_DIR)
    # write because single token for a user / API key => so maximum rights
    # or flickrapi will cause login each time
    flickr = create_flickr_api(api_key, api_secret, "write", token_cache_location)

    user = Addict(flickr.urls.lookupUser(url=flickr_album.url)).user
    user_id = user.id

    flickr_images_geo = get_geo_images_in_album(flickr, flickr_album.album_id, user_id)

    if len(flickr_images_geo) == 0:
        logger.warning(
            "No georeferenced image found in album! No KML will be generated."
        )
        return

    write_kml(
        flickr_images_geo,
        template,
        name_template,
        is_pushpin,
        template_args,
        output_kml_path,
    )


DEFAULT_CONFIG_FILENAME = "flickr_api_credentials.txt"
DEFAULT_APP_DIR = "flickr2kml"
DEFAULT_CONFIG_PATH = f"{click.get_app_dir(DEFAULT_APP_DIR)}/{DEFAULT_CONFIG_FILENAME}"

CONFIG_FILE_HELP = (
    f"Path to optional config file for the Flickr API credentials [default :"
    f" {DEFAULT_CONFIG_PATH}]"
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
    help=(
        "Choice of format for the placemark description, either predefined (gearth "
        "[default], mymaps) or as a path to a custom template"
    ),
    default="gearth",
)
@click.option(
    "-n",
    "--name_template",
    "name_template",
    help=(
        "Choice of format for the placemark name, as a path to a custom template "
        "[default: empty]"
    ),
    default="",
)
@click.option(
    "-a",
    "--template_arg",
    "template_args",
    multiple=True,
    help=("Variable to pass to the template (multiple possible)"),
    required=False,
)
@click.option(
    "-p",
    "--pushpin",
    "is_pushpin",
    is_flag=True,
    help=("Flag to make each placemark a simple pushpin instead of a small image"),
    required=False,
)
@click_config_file.configuration_option(
    "--config",
    "config_path",
    help=CONFIG_FILE_HELP,
    cmd_name=DEFAULT_APP_DIR,
    config_file_name=DEFAULT_CONFIG_FILENAME,
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
