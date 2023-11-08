from ..db_class.db import db
from ..db_class.db import Taxonomy, Tags
from .utils import taxonomies


def create_tag(tag, taxo_id):
    # if not Tags.query.filter_by(name=tag).first():
    revert_match = taxonomies.revert_machinetag(tag)[1].colour
    if not revert_match:
        namespace = tag.split(":")[0]
        
        list_to_search = list(taxonomies.get(namespace).machinetags())
        taxo_len = len(list_to_search)
        index = list_to_search.index(tag)
            
        color_list = generate_palette_from_string(namespace, taxo_len)
        color_tag = color_list[index]
    else:
        color_tag = revert_match

    tag_db = Tags(name=tag, color=color_tag, taxonomy_id=taxo_id)
    db.session.add(tag_db)
    db.session.commit()

def create_taxonomies():
    for taxonomy in list(taxonomies.keys()):
        if not Taxonomy.query.filter_by(name=taxonomy).first():
            taxo = Taxonomy(
                name = taxonomy,
                description = taxonomies.get(taxonomy).description
            )
            db.session.add(taxo)
            db.session.commit()

            for tag in taxonomies.get(taxonomy).machinetags():
                create_tag(tag, taxo.id)



def generate_palette_from_string(s, items):
    hue = str_to_num(s)
    saturation = 1
    steps = 80 / items
    results = []
    for i in range(items):
        value = (20 + (steps * (i + 1))) / 100
        rgb = hsv_to_rgb([hue, saturation, value])
        results.append(rgb)
    return results

def str_to_num(s):
    char_code_sum = 0
    for char in s:
        char_code_sum += ord(char)
    return (char_code_sum % 100) / 100

def hsv_to_rgb(hsv):
    H, S, V = hsv
    H = H * 6
    I = int(H)
    F = H - I
    M = V * (1 - S)
    N = V * (1 - S * F)
    K = V * (1 - S * (1 - F))
    rgb = []
    
    if I == 0:
        rgb = [V, K, M]
    elif I == 1:
        rgb = [N, V, M]
    elif I == 2:
        rgb = [M, V, K]
    elif I == 3:
        rgb = [M, N, V]
    elif I == 4:
        rgb = [K, M, V]
    elif I == 5 or I == 6:
        rgb = [V, M, N]
    return convert_to_hex(rgb)

def convert_to_hex(color_list):
    color = "#"
    for element in color_list:
        element = round(element * 255)
        element = format(element, '02x')
        if len(element) == 1:
            element = '0' + element
        color += element
    return color