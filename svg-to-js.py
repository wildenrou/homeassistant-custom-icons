# Convert SVG icons to JS format for HomeAssistant
import os
from pathlib import Path
from xml.dom import Node
from xml.dom.minidom import parseString

# Icon prefix in Home Assistant
ICONS_PREFIX = "custom"


def circle_to_path(circle):
    # Convert circle to path https://www.smashingmagazine.com/2019/03/svg-circle-decomposition-paths/
    cx = float(circle.getAttribute('cx'))
    cy = float(circle.getAttribute('cy'))
    r = float(circle.getAttribute('r'))
    return f"M {cx - r}, {cy} a {r},{r} 0 1,0 {r * 2},0 a {r},{r} 0 1,0 -{r * 2},0"


def polygon_to_path(polygon):
    # Convert polygon to path https://stackoverflow.com/questions/10717190/convert-svg-polygon-to-path
    points = polygon.getAttribute('points').strip()
    return f"M{points}z"


def polyline_to_path(polygon):
    # Convert polyline to path https://stackoverflow.com/questions/10717190/convert-svg-polygon-to-path
    points = polygon.getAttribute('points').strip()
    return f"M{points}"


def rect_to_path(rect):
    # Convert rect to path https://github.com/elrumordelaluz/element-to-path/blob/master/src/index.js
    x = float(rect.getAttribute('x'))
    y = float(rect.getAttribute('y'))
    w = float(rect.getAttribute('width'))
    h = float(rect.getAttribute('height'))
    rx = 0  # TODO curves
    ry = 0  # TODO curves
    return f"M{x + rx} {y} H{x + w - rx} V{y + h - ry} H{x + rx} V{y + ry}z"


def ellipse_to_path(ellipse):
    # Convert ellipse to path https://github.com/elrumordelaluz/element-to-path/blob/master/src/index.js
    cx = float(ellipse.getAttribute('cx'))
    cy = float(ellipse.getAttribute('cy'))
    rx = float(ellipse.getAttribute('rx'))
    ry = float(ellipse.getAttribute('ry'))
    return f"M{cx + rx} {cy} A{rx} {ry} 0 0 1 {cx} {cy + ry} A{rx} {ry} 0 0 1 {cx - rx} {cy} A{rx} {ry} 0 0 1 {cx + rx} {cy} z"


# Beginning of file
js = open("custom-icons.js", 'w')
js.write("""var icons = {
""")

# Browe all icons from icon-svg folder
for filename in sorted(os.listdir("icon-svg")):
    icon = os.path.join("icon-svg", filename)
    # checking if it is a file
    if os.path.isfile(icon) and filename != '.DS_Store':
        svg = open(icon, 'r').read()

        # Parse SVG as XML
        xml = parseString(svg)

        icon_name = Path(icon).stem
        try:
            # Look into all direct child nodes (and nodes inside "g") to detect unsupported SVG content
            incompatible = False
            nodes = xml.getElementsByTagName("svg")[0].childNodes + xml.getElementsByTagName("svg")[
                0].getElementsByTagName("g")
            for g_node in xml.getElementsByTagName("svg")[0].getElementsByTagName("g"):
                nodes += g_node.childNodes
            for node in nodes:
                if (node.nodeType == Node.ELEMENT_NODE
                        and node.nodeName != "path"
                        and node.nodeName != "g"
                        and node.nodeName != "circle"
                        and node.nodeName != "polygon"
                        and node.nodeName != "polyline"
                        and node.nodeName != "rect"
                        and node.nodeName != "ellipse"
                ):
                    print("Incompatible icon %s : contains \"%s\" element" % (icon, node.nodeName))
                    incompatible = True
            if incompatible:
                # Do not process this icon if incompatible SVG content is found
                continue

            # Convert viewBox data
            viewbox = xml.getElementsByTagName("svg")[0].getAttribute('viewBox').replace(" ", ",")

            # Convert supported SVG content, because HomeAssistant only supports data in the "path" format
            if (len(xml.getElementsByTagName("path")) >= 1
                    or len(xml.getElementsByTagName("circle")) >= 1
                    or len(xml.getElementsByTagName("polygon")) >= 1
                    or len(xml.getElementsByTagName("polyline")) >= 1
                    or len(xml.getElementsByTagName("rect")) >= 1
                    or len(xml.getElementsByTagName("ellipse")) >= 1
            ):
                data = ""
                for path in xml.getElementsByTagName("path"):
                    data += path.getAttribute('d') + " "
                for circle in xml.getElementsByTagName("circle"):
                    data += circle_to_path(circle) + " "
                for polygon in xml.getElementsByTagName("polygon"):
                    data += polygon_to_path(polygon) + " "
                for polyline in xml.getElementsByTagName("polyline"):
                    data += polyline_to_path(polyline) + " "
                for rect in xml.getElementsByTagName("rect"):
                    data += rect_to_path(rect) + " "
                for ellipse in xml.getElementsByTagName("ellipse"):
                    data += ellipse_to_path(ellipse) + " "

                # Write result to .js file
                js.write("  \"%s\":[%s,\"%s\"],\n" % (icon_name, viewbox, data))

                # For debug purposes, also generate an SVG with the converted content
                svg_converted = open(os.path.join("icon-svg", "converted", filename), 'w').write(
                    f"""<svg viewBox="{xml.getElementsByTagName("svg")[0].getAttribute('viewBox')}" xmlns="http://www.w3.org/2000/svg">
  <path d="{data}" />
</svg>""")
            else:
                print("Incompatible icon %s : %d paths" % (icon, len(xml.getElementsByTagName("path"))))
        except Exception as e:
            print("Incompatible icon %s : %s" % (icon, e))

# End of .js file
js.write("""  }

async function getIcon(name) {
  if (!(name in icons)) {
    console.log(`Icon "${name}" not available`);
    return '';
  }

  var svgDef = icons[name];
  var primaryPath = svgDef[4];
  return {
    path: primaryPath,
    viewBox: svgDef[0] + " " + svgDef[1] + " " + svgDef[2] + " " + svgDef[3]
  }

}

async function getIconList() {
  return Object.entries(icons).map(([icon]) => ({
    name: icon
  }));
}

window.customIconsets = window.customIconsets || {};
window.customIconsets[\"""" + ICONS_PREFIX + """\"] = getIcon;

window.customIcons = window.customIcons || {};
window.customIcons[\"""" + ICONS_PREFIX + """\"] = { getIcon, getIconList };
""")
js.close()
