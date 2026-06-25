<img title="" src="./doc/images/flowintel_logo.png" alt="" width="149" data-align="center">

Flowintel is an open-source platform designed to assist analysts in organizing their cases and tasks. It features a range of tools and functionalities to enhance workflow efficiency.

## Features

- **Case and Task Management**: Tailored for security analysts, enabling efficient tracking and organization.

- **Rich Documentation Tools**: Includes Markdown and Mermaid integration for detailed notes, with export options like PDF.

- **Integration with MISP standard**: Seamless connection with [MISP taxonomies](https://github.com/MISP/misp-taxonomies) and [MISP galaxy](https://www.misp-galaxy.org/).

- **Calendar and Notifications**: Features an efficient calendar view and notifications for timely task management.

- **Templating System**: Provides templates for cases and tasks, creating a playbook and process repository for cybersecurity.

- **Flexible Data Export**: Offers modules for exporting data to platforms like [MISP](https://www.misp-project.org/), [AIL](https://www.ail-project.org/), and more.

- **Accessible API**: Exposes an API for easy interaction with FlowIntel's functionalities.

- **Advanced Analysis Modules**: Leverages MISP modules for automated enrichment, threat intelligence, and data correlation.

- **User and Workflow Management**: Supports organizational structuring, task assignments, and a queueing system for efficient workload distribution.

- **Comprehensive Audit Logging**: Maintains a full audit trail of all actions, ensuring transparency and compliance.

![task-management](./doc/images/case_example.png)

## Quick start

### Prerequisites

- Python 3.10+
- PostgreSQL (or SQLite, MySQL, MariaDB)
- Valkey (or Redis)
- uv (for Python dependency management)
- Bun (for Node.js dependency management)

### Installation

1. **Copy the default configuration**:

```bash
cd flowintel
cp conf/config.py.default conf/config.py
cp conf/config_module.py.default conf/config_module.py
```

2. **Configure** the application in `conf/config.py`

3. **Run the installation script**:

```bash
./install.sh
```

4. **Start** the application:

```bash
./launch.sh -l
```

### MacOS
In `/bin` there's a script for installation and for launching

#### Account

- email: `admin@admin.admin`
- password: `admin`

## Available Commands

### launch.sh

```bash
./launch.sh -l               # Development launch
./launch.sh -ld              # Docker launch
./launch.sh -i               # Initialize database
./launch.sh -ip              # Production database initialization
./launch.sh -r               # Recreate database
./launch.sh -p               # Production launch
./launch.sh -t               # Run tests
./launch.sh -ks              # Kill running sessions
./launch.sh -tg              # Update taxonomies and galaxies
./launch.sh -mm              # Update MISP modules
./launch.sh -tdc <key>       # Create community test data
./launch.sh -dtdc <key>      # Delete community test data
./launch.sh -tdcc            # Create test cases
./launch.sh -dtdcc           # Delete test cases
```

## Using vite

To build assets using vite:

```bash
cd app/assets
bun run build:static
```

Or with npm:

```bash
cd app/assets
npm run build:static
```

## Adding Custom Taxonomies/Galaxies

If you would like to add your own galaxies and taxonomies to Flowintel, add it to:

- `flowintel/modules/custom_taxonomies/`

- `flowintel/modules/custom_galaxies/`

Just keep in mind that for taxonomies a `MANIFEST.json` is required and for galaxies two folders `clusters` and `galaxies`

See: [misp-galaxy](https://github.com/MISP/misp-galaxy), [misp-taxonomies](https://github.com/MISP/misp-taxonomies)

## Makefile helper
A Makefile helper is provided with this repo, it should work on Linux and modern MacOS.
For the later, prefer ```gmake```, from Homebrew for example, for maximal compatibility although the modern BSD ```make``` versions shipped with modern MacOS seem compatible with the current Makefile wprkflows.

The Makefile is self documented, type ```make help``` for further information.

In a few line, it provide helper targerts to facilitate various Development workflows and keeping Development environments and installation harmonized.
Examples of usage:
1. Start the application fully containerised with a MariaDB backend and an empty databse: ```make nuke_volume;make runfull_maria```
2. Build the latest local image: ```make build_latest_local```
3. Run the datastack local Development infrastructure with Postgres: ```make dev_localinfra_postgres_run```
4. ***Still experimental*** Run the application in it own Python local Virtual Environment alongside the datastack local Development infrastructure with MariaDB: ```make run_maria```
5. Initial the repository installing locally the Python Virtual Environment and deriving default config: ```make first_install```

## Dockerised deployment
The deployment can be conducted using Docker in Development, Testing and Production environment. Different flavors of the
software architecture can be spawned with different Docker Composition files that can be found in ```docker``` folder.

It should be remarked that currently the Docker images includes the Git submodules (MISP taxonomy, galaxy, objects) for legacy reason.
In the future, these folders may be directly mounted at runtime to provide more update flexibity.

A distinction is to be made in between:
1. ```docker-compose.yml``` file that use the online Docker Image alongside dockerised Valkey and Postgres instances,
2. ```docker-compose-local-*.yml``` files that presuppose that the user built locally a Docker image of the Application.

For the later case, there are 8 variations of them:
1. composition files making the assumption of a Postgres backend:
- ```docker-compose-local-flowintel-full-postgres.yml```: latest local image, full stack with all services (database, Valkey, Flowintel), defaults to Postgres (most likely situation for local development with a fully containerised local infrastructure),
- ```docker-compose-local-flowintel-infra-postgres.yml```: latest local image, datastack infrastructure only (database, Valkey), defaults to Postgres (most likely situation for local development with Flowintel deployment on a development machine with a local Python Virtual Environment and relying on datastack containerised local infrastructure,
- ```docker-compose-local-flowintel-nodb-postgres.yml```: latest local image, Flowintel and Valkey but ***no*** databse service, defaults to Postgres (most likely situation in Production),
- ```docker-compose-local-flowintel-single-postgres.yml```: latest local image, single Flowintel service, defaults to Postgres.
2. composition files making the assumption of a MariaDB backend:
- ```docker-compose-local-flowintel-full-maria.yml```: latest local image, full stack with all services (database, Valkey, Flowintel), defaults to MariaDB (most likely situation for local development with a fully containerised local infrastructure),
- ```docker-compose-local-flowintel-infra-maria.yml```: latest local image, datastack infrastructure only (database, Valkey), defaults to MariaDB (most likely situation for local development with Flowintel deployment on a development machine with a local Python Virtual Environment and relying on datastack containerised local infrastructure),
- ```docker-compose-local-flowintel-nodb-maria.yml```: latest local image, Flowintel and Valkey but ***no*** databse service, defaults to MariaDB (most likely situation in Production),
- ```docker-compose-local-flowintel-single-maria.yml```: latest local image, single Flowintel service, defaults to MariaDB.

Note: These files are predefined and more easily used in combination with the ```Makefile``` helper.

## Roadmap

Overview of features currently under development.
https://github.com/orgs/flowintel/projects/5

## License

This software is licensed under [GNU Affero General Public License version 3](http://www.gnu.org/licenses/agpl-3.0.html)

```
Copyright (C) 2022-2023 CIRCL - Computer Incident Response Center Luxembourg
Copyright (C) 2022-2023 David Cruciani
```

## Funding

Flowintel is co-funded by [CIRCL](https://www.circl.lu/) and by the European Union under [FETTA](https://www.circl.lu/pub/press/20240131/) (Federated European Team for Threat Analysis) project.

![EU logo](https://www.vulnerability-lookup.org/images/eu-funded.jpg)
