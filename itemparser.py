from bs4 import BeautifulSoup, NavigableString, Tag
import re

# styles = {
#     "-mod": "#%s",
#     "-value": "**%s**",
#     "-flavour": "*%s*",
#     "-corrupted": "%s"
# }

hide_string = "#####&#009;\n\n######&#009;\n\n####&#009;\n\n%s\n\n***\n\n"

def parse_item(panel):
    panel = panel.replace("<br>", "<br/>") #BeautifulSoup does not seem to correctly parse <br>, so we add the /.
    panel = fix_wiki_links(panel)
    soup = BeautifulSoup(panel, "html.parser")
    # Find div with class item-box. Only unique items so far..
    itembox = soup.find("span", { "class": "item-box" })
    if not itembox or "-unique" not in itembox["class"]: return ""
    header = itembox.find("span", { "class": "header" })
    unique_name = unicode(header.children.next())
    base_item = unicode(header.children.next().next.next)
    
    unparsed_groups = itembox.find("span", { "class": "item-stats" }).find_all("span", { "class": "group" })
    
    groups = []
    for group in unparsed_groups:
        lines = []
        line = ""
        for child in flatten(group.extract()):
            if not unicode(child).strip():
                continue #Ignore whitespace lines.
            elif unicode(child) == '<br/>':
                lines.append(line)
                line = ""
            else:
                line += format_text(child, line == "") or ""
        if line is not "":
            lines.append(line)
        groups.append(lines)
    item_string = make_string(unique_name, base_item, groups)
    #return (hide_string % unique_name) + item_string + "\n\n" #Add hiding.. Shows "GGG forum post. Hover to view.".
    return item_string + "\n\n"

pattern = re.compile("\[\[([^\[\]]*)\]\]")
def fix_wiki_links(panel):
    return pattern.sub(build_link, panel)

def build_link(match):
    content = match.group(1)
    split = content.split("|")
    link = split[0]
    text = split[len(split) - 1] #The last element, either 0 or 1.
    #Do I want to build a link here..?
    return text

def flatten(tag):
    next = tag.next_element
    count = len(tag.contents)
    while tag is not None:
        if (type(next) == NavigableString and count == 1):
            yield tag
            (tag, next, count) = get_next(tag, next)
        elif count == 0:
            yield tag
        (tag, next, count) = get_next(tag, next)

def get_next(tag, next):
    tag = next
    if next is not None:
        next = next.next_element
    count = None
    if tag is not None:
        if type(tag) == NavigableString:
            count = 0
        else:
            count = len(tag.contents)
    return (tag, next, count)

def parse_item_fallback(page):
    soup = BeautifulSoup(page, "html.parser")
    # Find div with class item-box. Only unique items so far..
    itembox = soup.find("div", { "class": "item-box" })
    if not itembox or "-unique" not in itembox["class"]: return ""
    header = itembox.find("span", { "class": "header" })
    unique_name = header.children.next().text
    base_item = header.find("a").text
    
    unparsed_groups = itembox.find("span", { "class": "item-stats" }).find_all("span", { "class": "group" })
    
    groups = []
    for group in unparsed_groups:
        lines = []
        line = ""
        for child in group.children:
            if not unicode(child).strip():
                continue #Ignore whitespace lines.
            elif unicode(child) == '<br/>':
                lines.append(line)
                line = ""
            else: 
                line += format_text(child) or ""
        if line is not "":
            lines.append(line)
        groups.append(lines)
    item_string = make_string(unique_name, base_item, groups)
    #return (hide_string % unique_name) + item_string + "\n\n" #Add hiding.. Shows "GGG forum post. Hover to view.".
    return item_string + "\n\n"

def format_text(child, start_of_line = True):
    if type(child) == NavigableString:
        classes = child.parent.get("class")
    elif type(child) == Tag and child.name == 'br':
        classes = child.parent.get("class")
    else:
        classes = child.get("class")

    if not classes:
        return child.string

    if "-value" in classes:
        return "**%s**" % child.string
    elif "-corrupted" in classes:
        return child.string
    elif "-fire" in classes:
        return "**%s**" % child.string #Should be red, but not possible.
    elif "-cold" in classes:
        return "**%s**" % child.string #Should be blue, but not possible.
    elif "-lightning" in classes:
        return "**%s**" % child.string #Should be yellow, but not possible.
    elif "-mod" in classes: 
        if start_of_line: 
            return "#%s" % child.string
        else:
            return "**%s**" % child.string # We can't make blue text in only parts of a line.
    elif "-flavour" in classes: 
        return "*%s*\n>>" % child.string.strip()
    else:
        return child.string

def make_string(name, base, groups):
    s = ">######%s[](#break)%s\n" % (name, base)
    #s = ">######[%s](%s)[](#break)%s\n" % (name, link, base) #also include link in the header..
    for group in groups:
        for line in group:
            s += ">>%s%s\n" % ("" if line.startswith("*") else "####", line)
        s += ">>[](#line)\n"
    if len(groups) > 0:
        s = s[:-13]
    return s