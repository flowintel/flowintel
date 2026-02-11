import os
import json
import glob
from ..db_class.db import db
from ..db_class.db import Taxonomy, Tags, Galaxy, Cluster

from pytaxonomies import Taxonomies
from pymispgalaxies import Galaxies, Clusters


def get_taxonomies():
    manifest = os.path.join(os.getcwd(), "modules/misp-taxonomies/MANIFEST.json")
    return Taxonomies(manifest_path=manifest)

def get_galaxies():
    galaxies_list = []
    root_dir_galaxies = os.path.join(os.getcwd(), 'modules/misp-galaxy/galaxies')
    for galaxy_file in glob.glob(os.path.join(root_dir_galaxies, '*.json')):
        with open(galaxy_file, 'r') as f:
            galaxies_list.append(json.load(f))

    clusters_list = []
    root_dir_clusters = os.path.join(os.getcwd(), 'modules/misp-galaxy/clusters')
    for galaxy_file in glob.glob(os.path.join(root_dir_clusters, '*.json')):
        with open(galaxy_file, 'r') as f:
            clusters_list.append(json.load(f))

    return Galaxies(galaxies=galaxies_list), Clusters(clusters=clusters_list)

def delete_double_tag(tag):
    tag_db = Tags.query.filter_by(name=tag).all()
    if len(tag_db) > 1:
        for tag in tag_db:
            if not tag.uuid:
                db.session.delete(tag)
                db.session.commit()
                break

def create_tag_db(loc_tag, tag, taxonomy: Taxonomy, taxonomies: Taxonomies, taxo_id: int):
    loc_colour = loc_tag.colour
    loc_uuid = loc_tag.uuid
    loc_description = loc_tag.description
    if not loc_colour:
        namespace = taxonomy
        
        list_to_search = list(taxonomies.get(namespace).machinetags())
        index = list_to_search.index(tag)
            
        color_list = generate_palette_from_string(namespace, len(list_to_search))
        color_tag = color_list[index]
    else:
        color_tag = loc_colour

    tag_db = Tags.query.filter_by(uuid=loc_uuid).first()
    if not tag_db:
        tag_db = Tags.query.filter_by(name=tag).first()
    if not tag_db:
        tag_db = Tags(
            name=tag, 
            color=color_tag, 
            description=loc_description, 
            taxonomy_id=taxo_id,
            uuid=loc_uuid
            )
        db.session.add(tag_db)
        db.session.commit()
    else:
        tag_db.name = tag
        tag_db.color = color_tag
        tag_db.description = loc_description
        tag_db.uuid = loc_uuid
        db.session.commit()

def create_tag(taxonomy: Taxonomy, taxo_id: int, taxonomies: Taxonomies):
    for p in taxonomies.get(taxonomy).values():
        if taxonomies.get(taxonomy).has_entries():
            for t in p.values():
                loc_tag = f'{taxonomy}:{p}="{t}"'
                create_tag_db(t, loc_tag, taxonomy, taxonomies, taxo_id)
        else:
            loc_tag = f'{taxonomy}:{p}'
            create_tag_db(p, loc_tag, taxonomy, taxonomies, taxo_id)


def create_taxonomies_core(taxonomies, install=False):
    for taxonomy in list(taxonomies.keys()):
        t = Taxonomy.query.filter_by(name=taxonomy).first()
        if not t:
            taxo = Taxonomy(
                name = taxonomy,
                description = taxonomies.get(taxonomy).description,
                version = taxonomies.get(taxonomy).version,
                uuid = taxonomies.get(taxonomy).taxonomy["uuid"]
            )
            db.session.add(taxo)
            db.session.commit()

            create_tag(taxonomy, taxo.id, taxonomies)
        else:
            if not install:
                if not t.version:
                    create_tag(taxonomy, t.id, taxonomies)

                    t.version = taxonomies.get(taxonomy).version
                    db.session.commit()
                if not t.uuid:
                    create_tag(taxonomy, t.id, taxonomies)

                    t.uuid = taxonomies.get(taxonomy).taxonomy["uuid"]
                    db.session.commit()

                if not t.version == taxonomies.get(taxonomy).version:
                    create_tag(taxonomy, t.id, taxonomies)

                    t.version = taxonomies.get(taxonomy).version
                    db.session.commit()

                create_tag(taxonomy, t.id, taxonomies)
                for tag in taxonomies.get(taxonomy).machinetags():
                    delete_double_tag(tag)

def create_taxonomies(install=False):
    if install:
        print("[+] Installing taxonomies...")
    else:   
        print("[+] Updating taxonomies...")
    taxonomies = get_taxonomies()
    print("[*] Load built-in taxonomies...")
    create_taxonomies_core(taxonomies, install)

    custom_taxonomies_path = os.path.join(os.getcwd(), 'modules/custom_taxonomies')
    if not os.path.exists(custom_taxonomies_path):
        return
    for custom_taxonomy in os.listdir(custom_taxonomies_path):
        if not os.path.isdir(os.path.join(custom_taxonomies_path, custom_taxonomy)):
            continue
        print(f"[*] Load custom taxonomy: modules/custom_taxonomies/{custom_taxonomy}...")
        custom_taxonomies = Taxonomies(manifest_path=os.path.join(custom_taxonomies_path, custom_taxonomy, 'MANIFEST.json'))
        create_taxonomies_core(custom_taxonomies, install)


def create_galaxies_core(galaxies, clusters, install=False):
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
        elif galaxy_db.version < current_galaxy.version and not install:
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

            elif cluster_db.version < current_cluster_info.version and not install:
                if current_cluster.meta:
                    meta = json.dumps(current_cluster.meta.to_json())
                else:
                    meta = ""
                cluster_db.name = cluster
                cluster_db.version = current_cluster_info.version
                cluster_db.description = current_cluster.description
                cluster_db.meta = meta
                db.session.commit()

def create_galaxies(install=False):
    if install:
        print("[+] Installing Galaxies...")
    else:
        print("[+] Updating Galaxies...")
    galaxies, clusters = get_galaxies()
    print("[*] Load built-in galaxies...")
    create_galaxies_core(galaxies, clusters, install)

    custom_galaxies_path = os.path.join(os.getcwd(), 'modules/custom_galaxies')
    if not os.path.exists(custom_galaxies_path):
        return
    
    for custom_galaxy in os.listdir(custom_galaxies_path):
        if not os.path.isdir(os.path.join(custom_galaxies_path, custom_galaxy)):
            continue
        print(f"[*] Load custom galaxy: modules/custom_galaxies/{custom_galaxy}...")
        custom_galaxies_list = []
        root_dir_galaxies = os.path.join(custom_galaxies_path, custom_galaxy, 'galaxies')
        for galaxy_file in glob.glob(os.path.join(root_dir_galaxies, '*.json')):
            with open(galaxy_file, 'r') as f:
                custom_galaxies_list.append(json.load(f))

        custom_clusters_list = []
        root_dir_clusters = os.path.join(custom_galaxies_path, custom_galaxy, 'clusters')
        for galaxy_file in glob.glob(os.path.join(root_dir_clusters, '*.json')):
            with open(galaxy_file, 'r') as f:
                custom_clusters_list.append(json.load(f))

        custom_galaxies, custom_clusters = Galaxies(galaxies=custom_galaxies_list), Clusters(clusters=custom_clusters_list)
        create_galaxies_core(custom_galaxies, custom_clusters, install)


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