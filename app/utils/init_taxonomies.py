import json
import os
from ..db_class.db import db
from ..db_class.db import Taxonomy, Tags, Galaxy, Cluster
from .utils import taxonomies, galaxies, clusters, check_tag


def create_tag(tag, taxo_id):
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

    description = taxonomies.revert_machinetag(tag)[1].description
    if not description:
        description = taxonomies.revert_machinetag(tag)[1].expanded
        if not description:
            description = ""

    tag_db = Tags(name=tag, color=color_tag, description=description, taxonomy_id=taxo_id)
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


def create_galaxies():
    for galaxy in list(galaxies.keys()):
        current_galaxy = galaxies.get(galaxy)
        galaxy_db = Galaxy.query.filter_by(uuid=current_galaxy.uuid).first()
        if not galaxy_db:
            galax = Galaxy(
                name = galaxy,
                uuid = current_galaxy.uuid,
                version = current_galaxy.version,
                description = current_galaxy.description,
                icon = current_galaxy.icon,
                type = current_galaxy.type
            )
            db.session.add(galax)
            db.session.commit()
        elif galaxy_db.version < current_galaxy.version:
            galaxy_db.name = current_galaxy.name
            galaxy_db.version = current_galaxy.version
            galaxy_db.description = current_galaxy.description
            galaxy_db.icon = current_galaxy.icon
            galaxy_db.type = current_galaxy.type
            db.session.commit()

    for cluster in list(clusters.keys()):
        current_cluster_info = clusters.get(cluster)
        for cl in list(current_cluster_info.keys()):
            current_cluster = current_cluster_info.get(cl)
            cluster_db = Cluster.query.filter_by(uuid=current_cluster.uuid).first()
            if not cluster_db:
                if current_cluster.meta:
                    meta = json.dumps(current_cluster.meta.to_json())
                else:
                    meta = ""

                cluster_created = Cluster(
                    name = cl,
                    uuid = current_cluster.uuid,
                    version = current_cluster_info.version,
                    description = current_cluster.description,
                    galaxy_id = Galaxy.query.filter_by(type=current_cluster_info.type).first().id,
                    tag = f'misp-galaxy:{cluster}="{cl}"',
                    meta = meta
                )

                db.session.add(cluster_created)
                db.session.commit()

            elif cluster_db.version < current_cluster_info.version:
                if current_cluster.meta:
                    meta = json.dumps(current_cluster.meta.to_json())
                else:
                    meta = ""
                cluster_db.name = cluster
                cluster_db.version = current_cluster_info.version
                cluster_db.description = current_cluster.description
                cluster_db.meta = meta
                db.session.commit()



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