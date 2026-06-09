# /!\ /!\ /!\ /!\ /!\ /!\ /!\ DISCLAIMER /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\/!\ /!\ /!\/!\
#
# This Makefile is only meant to be used for DEVELOPMENT purpose as we are
# changing the user id that will run in the container.
#
# PLEASE DO NOT USE IT FOR YOUR PRODUCTION...
#
# Ref:
#  - https://gitlab.com/tCR-lux/my-devops-playground/-/tree/master/Python/devloc
#  - https://github.com/NetCarapace/url-checker/blob/main/Makefile
# /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\/!\ /!\ /!\/!\
########################################################################################
# How-to use
########################################################################################
# Run the make with as follow:
#
# ```bash
# make ${make_target} \
#      version_repo="X.Y.Z" \
#      tag_message = "the message your may want to associate with the Git tag" \
# ```

BOLD := \033[1m
RESET := \033[0m
BLUE := \033[1;34m
GREEN := \033[1;32m
RED := \033[31m
BOLD_GREEN := \033[1;32m

########################################################################################
# PREAMBLE - OS AND DEPENDENCY CHECKS
########################################################################################
# Detect OS
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    $(info ✅ Running on Linux)
    OS := Linux
	# Detect package manager
    ifneq (,$(shell command -v apt 2> /dev/null))
        PKG_MANAGER := apt
    else ifneq (,$(shell command -v dnf 2> /dev/null))
        PKG_MANAGER := dnf
    else ifneq (,$(shell command -v yum 2> /dev/null))
        PKG_MANAGER := yum
    else ifneq (,$(shell command -v zypper 2> /dev/null))
        PKG_MANAGER := zypper
    else ifneq (,$(shell command -v pacman 2> /dev/null))
        PKG_MANAGER := pacman
    else
        $(error ❌ Unable to detect package manager (apt, dnf, yum, zypper, or pacman))
    endif
    $(info ✅ Package manager detected: $(PKG_MANAGER))
else ifeq ($(UNAME_S),Darwin)
    $(info ✅ Running on macOS)
    OS := macOS
else
    $(error ❌ Unsupported OS: $(UNAME_S). Only Linux and macOS are supported.)
endif
UNAME_S :=

# Check for bash

ifeq (,$(shell command -v bash 2> /dev/null))
    $(error ❌ bash not found. Please install bash.)
else
    $(info ✅ bash found: $(shell command -v bash))
endif

# Check for uv
ifeq (,$(shell command -v uv 2> /dev/null))
    $(error ❌ uv not found. Please install uv, ideally with your package manager, or from https://github.com/astral-sh/uv)
else
    UV_VERSION := $(shell uv --version 2>/dev/null)
    $(info ✅ uv found: $(UV_VERSION))
endif
UV_VERSION :=


########################################################################################
# VARIABLES
########################################################################################

# Use Bash and its facilities
SHELL := /bin/bash

# this one is to bump version, different from PACKAGE_VERSION which only reads Version state
version_repo = "0.0.0"
#
tag_message = ""

rebuild = 1

########################################################################################
# RULES
########################################################################################

.SILENT:
.PHONY: configure_repo_dev \
		clean \
		testclean \
		distclean \
		coverageclean \
		database_init
		dev_infra_run \
		dev_infra_maria_run \
		dev_infra_stop \
		run \
		run_maria \
		nuke

# Init
########################################################################################
configure_repo_dev:
	# In this project, the .env file is automatically run by the application
	# so we simply rely on switching postgres and mariadb environments at startup by
	# file permutation
	# We may add .envbuild file sources in the Makefile later
	cp -n template.env .env.postgres
	cp -n template.env .env.mariadb
	cp -n conf/config.py.default conf/config.py
	cp -n conf/config_module.py.default conf/config_module.py
	echo
	echo "The repository was configured for local dev running."
	echo
	echo -e "${BLUE}${BOLD}Please edit the files .env.postgres and .env.mariadb and conf/config.py before proceeding.${RESET}"
	# TODO add the install deps with uv recipes -> Development lifecycle
	echo -e "${BLUE}${BOLD}Do not forget to run the database_init recipe at first install, aftert the docker-compose spawned.${RESET}"
	echo
	echo "💣 DO NOT RUN IN PRODUCTION !!! Press Enter to continue or Ctrl+C to exit"
	read wait_for_me;
	uv venv;
	uv pip install -r requirements.txt

restore_requirements:
	echo "Restoring requirements files"
	cp -f requirements.txt.backup requirements.txt
	cp -f requirements.in.backup requirements.in

# Development lifecycle #
########################################################################################
# Dependencies

########################################################################################

# Database Management
database_init:
	# TODO Clarify how much it is redundant with migrate.sh script
	# TODO Clarify why we even need it for Docker as it seems to be already managed in the entrypoint
	@echo "💣 DO NOT RUN IN PRODUCTION !!!";
	echo "${RED}First run the application, then run this recipe at first install only.${RESET}"
	go_to_initdb="N"; \
	read -p "Do you want to continue ? (Y/N) " go_to_initdb; \
	if [ $$go_to_initdb = "Y" ] || [ $$go_to_initdb = "y" ]; then \
		docker exec -it flowintel bash -i ./launch.sh --init_db; \
		echo "Database initialized."; \
	else \
		echo "Database initialization skipped."; \
	fi; \

init_migrations:
	# TODO Clarify how much it is redundant with migrate.sh script
	@echo "💣 DO NOT RUN IN PRODUCTION !!! Press Enter to continue or Ctrl+C to exit";
	read wait_for_me; \
	uv run flask db init
	uv run flask db migrate -m "initial schema"

new_migration: dev_localinfra_run
	@echo "💣 DO NOT RUN IN PRODUCTION !!! Press Enter to continue or Ctrl+C to exit";
	echo "Install the application in Dockerised Local Dev Infra first";
	read wait_for_me; \
	echo "Waiting 5 seconds for database available..."
	sleep 5
	# Just if case, should be harmless
	VENV_DIR=".venv" ./launch.sh -i
	#
	VENV_DIR=".venv" ./migrate.sh --upgrade --env production
	echo "Database initialised and upgraded, when necessary applied"
	VENV_DIR=".venv" ./migrate.sh --migrate --env production
	echo "New migrations created, when applicable"
	VENV_DIR=".venv" ./migrate.sh --upgrade --env production
	echo "New migrations applied"
	# Stop test infra (not functionnal yet, might need utilities scripts)
	docker compose -f docker-compose-localinfra-pg.yml down


new_migration_maria: dev_localinfra_maria_run
	set -e; \
	trap '$(MAKE) restore_requirements' EXIT; \
	echo "💣 DO NOT RUN IN PRODUCTION !!! Press Enter to continue or Ctrl+C to exit"; \
	echo "Install the application in Dockerised Local Dev Infra first"; \
	read wait_for_me; \
	echo "Waiting 5 seconds for database available..."; \
	sleep 5; \
	cp -f requirements.txt requirements.txt.backup; \
	cp -f requirements.in requirements.in.backup; \
	sed -i '/^psycopg2/d' requirements.txt; \
	echo 'PyMySQL>=1.1.0' >> requirements.txt; \
	sed -i '/^psycopg2/d' requirements.in; \
	echo 'PyMySQL' >> requirements.in; \
	# Just if case, should be harmless; \
	VENV_DIR=".venv" ./launch.sh -i; \
	#; \
	VENV_DIR=".venv" ./migrate.sh --upgrade --env production; \
	echo "Database initialised and upgraded, when necessary applied"; \
	VENV_DIR=".venv" ./migrate.sh --migrate --env production; \
	echo "New migrations created, when applicable"; \
	VENV_DIR=".venv" ./migrate.sh --upgrade --env production; \
	echo "New migrations applied"; \
	# Stop test infra (not functionnal yet, might need utilities scripts); \
	docker compose -f docker-compose-localinfra-maria.yml down;

full_new_migration:
	# TODO Clarify how much it is redundant with migrate.sh script
	# STILL EVEN MORE EXPERIMENTAL
	@echo "💣 DO NOT RUN IN PRODUCTION !!! Press Enter to continue or Ctrl+C to exit";
	echo "The application must already be run in full Docker mode"
	read wait_for_me; \
	echo "Waiting 5 seconds for database available..."
	sleep 5
	docker exec -it flowintel bash -i ./migrate.sh --migrate
	echo "New migration created if new model found"
	sleep 1
	docker exec -it flowintel bash -i ./migrate.sh --upgrade
	echo "New migrations applied"
	# Stop test infra (not functionnal yet, might need utilities scripts)
	docker compose -f docker-compose-localinfra-pg.yml down


full_new_migration_maria:
	# TODO Clarify how much it is redundant with migrate.sh script
	# STILL EVEN MORE EXPERIMENTAL
	# TODO Clarify how much it is redundant with migrate.sh script
	@echo "💣 DO NOT RUN IN PRODUCTION !!! Press Enter to continue or Ctrl+C to exit";
	echo "The application must already be run in full Docker mode"
	read wait_for_me; \
	echo "Waiting 5 seconds for database available..."
	sleep 5
	docker exec -it flowintel bash -i ./migrate.sh --migrate
	echo "New migration created if new model found"
	sleep 1
	docker exec -it flowintel bash -i ./migrate.sh --upgrade
	echo "New migrations applied"
	# Stop test infra (not functionnal yet, might need utilities scripts)
	docker compose -f docker-compose-localfull-maria.yml down

# Run Application
# TODO in the future, either build a New image to account for WebApp changes
# or make a specific "run_dev" to run locally the app and simply spawn databases and
# Valkey as "dev_infra" like we did for URLChecker Web Platform
run: configure_repo_dev dev_localinfra_run
	VENV_DIR=".venv" ./install.sh
	VENV_DIR=".venv" ./launch.sh -l
	echo "Press Enter to close..."
	read _
	sleep 1
	# Stop test infra (not functionnal yet, might need utilities scripts)
	docker compose -f docker-compose-localinfra-pg.yml down

run_maria: configure_repo_dev dev_localinfra_maria_run
	set -e; \
	trap '$(MAKE) restore_requirements' EXIT; \
	cp -f requirements.txt requirements.txt.backup; \
	cp -f requirements.in requirements.in.backup; \
	sed -i '/^psycopg2/d' requirements.txt; \
	echo 'PyMySQL>=1.1.0' >> requirements.txt; \
	sed -i '/^psycopg2/d' requirements.in; \
	echo 'PyMySQL' >> requirements.in; \
	
	VENV_DIR=".venv" ./install.sh; \
	VENV_DIR=".venv" ./launch.sh -l; \
	
	echo "Press Enter to close..."; \
	read _; \
	sleep 1; \
	# Stop test infra (not functionnal yet, might need utilities scripts); \
	docker compose -f docker-compose-localinfra-maria.yml down

runfull: configure_repo_dev build_latest_local
	cp -f .env.full.postgres .env
	docker compose -f docker-compose-localfull-pg.yml up
	echo "Press Enter to close..."
	read _
	sleep 1
	# Stop test infra (not functionnal yet, might need utilities scripts)
	docker compose -f docker-compose-localfull-pg.yml down

runfull_maria: configure_repo_dev build_maria_latest_local
	cp -f .env.full.mariadb .env
	docker compose -f docker-compose-localfull-maria.yml up
	echo "Press Enter to close..."
	read _
	sleep 1
	# Stop test infra (not functionnal yet, might need utilities scripts)
	docker compose -f docker-compose-localfull-maria.yml down
########################################################################################

# Build 🌍 , Publish  🌬️ and Release 🔥
build_latest_local: nuke
ifeq ($(rebuild),1)
	@echo "Image Rebuild rebuild requested"
	docker build -f DockerfilePostgres -t flowintel:latest .
else
	@echo "Image Rebuild skipped"
endif

build_maria_latest_local: nuke
ifeq ($(rebuild),1)
	set -e; \
	trap '$(MAKE) restore_requirements' EXIT; \
	echo "Image Rebuild rebuild requested"; \
	cp -f requirements.txt requirements.txt.backup; \
	cp -f requirements.in requirements.in.backup; \
	sed -i '/^psycopg2/d' requirements.txt; \
	echo 'PyMySQL>=1.1.0' >> requirements.txt; \
	sed -i '/^psycopg2/d' requirements.in; \
	echo 'PyMySQL' >> requirements.in; \
	docker build -f DockerfileMaria -t flowintel_maria:latest .
else
	@echo "Image Rebuild skipped"
endif

# Various Helpers
dev_localinfra_run:
	cp -f .env.postgres .env
	docker compose -f docker-compose-localinfra-pg.yml up

dev_localinfra_maria_run:
	cp -f .env.mariadb .env
	docker compose -f docker-compose-localinfra-maria.yml up

dev_localinfra_stop:
	docker compose -f docker-compose-localinfra-pg.yml down

dev_localinfra_maria_stop:
	docker compose -f docker-compose-localinfra-maria.yml down

################
# Housekeeping #
################
format_and_lint:
	uv run pre-commit run --all-files --show-diff-on-failure --verbose;

bump_version: version
ifeq (${version_repo},"0.0.0")
	@echo "❌ Provide version_repo=X.Y.Z on CLI"
	@echo "Usage: make bump_version version_repo=1.2.3"
else
	@echo "✅ Ensure clean working directory first"
	@if ! git diff-index --quiet HEAD --; then \
		echo "❌ Working directory is dirty. Commit or stash changes first."; \
		exit 1; \
	fi

	@echo "🔄 Pulling latest changes..."
	git pull

	@echo "📝 Bumping repo to version ${version_repo}"
	echo ${version_repo} > version
	sed -i "s/.*version =.*/version = \"${version_repo}\"/" "pyproject.toml"

	@echo "🔒 Updating uv.lock..."
	uv lock

	@echo "📦 Staging changes..."
	git add version
	git add "pyproject.toml"
	git add uv.lock

	@echo "💾 Committing changes..."
	git commit -m "BUMP to version ${version_repo}"

	@echo "🏷️  Creating tag ${version_repo}..."
	git tag ${version_repo} -m "${tag_message}"

	@echo "🚀 Pushing to remote..."
	git push
	git push --tags

	@echo "✅ Version bumped to ${version_repo}"
endif

clean:
	-find . -name __pycache__ -print0 | xargs -0 rm -rf
	-find . -name "*.pyc" -print0 | xargs -0 rm -rf
	-find . -name "*.egg-info" -print0 | xargs -0 rm -rf

coverageclean:
	.coverage
	.coverage.*
	coverage.xml
	-rm -rf htmlcov

distclean:
	-rm -rf ./dist
	-rm -rf ./build
	-rm -rf ./.venv
	-rm -rf logs
	-rm -rf modules/misp-galaxy
	-rm -rf modules/misp-objects
	-rm -rf modules/misp-taxonomies

nuke: clean distclean testclean

nuke_volume:
	@echo "💣 DO NOT RUN IN PRODUCTION !!! Press Enter to continue or Ctrl+C to exit"
	@echo "💣 DO NOT RUN IN DEV IF YOU NEED TO KEEP OTHER APP VOLUMES !!! Press Enter to continue or Ctrl+C to exit"
	read wait_for_me
	docker volume rm flowintel_db -f
	docker volume rm flowintel_flowintel-data -f
	docker volume rm flowintel_valkey-data -f
	#docker volume prune -f
	#docker system prune --volumes

# TODO nuke_dev_infra > docker volumes, networks (and images ?)

########################################################################################


################
# Makefile Doc #
################

help :
	echo ""
	echo -e "${BLUE}${BOLD}### I am your quick and dirty Help file :) ###${RESET}"
	echo ""
	echo -e "${GREEN}${BOLD}# Run make with targets like:${RESET}"
	echo "make target someparameter=\"somevalue\""
	echo ""
	echo -e "${GREEN}# Available combinations arguments/targets/description:${RESET}"
	echo ""
	echo -e "${BOLD}🛠️  Initialize local dev environment:${RESET}"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "configure_repo_dev" "/" "Configure local .env files (TODO: + Python3 venv + pre-commit hooks)"
	echo ""
	echo -e "${BOLD}📦 Development lifecycle:${RESET}"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "database_init" "/"  "Initialise database when run fully Dockerised- Run only on first install IN DEV !"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "new_migration" "/"  "Create a new migration file, Postgresql running as Dockerised Dev Infrastructure"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "new_migration_maria" "/"  "Create a new migration file, MariaDB running as Dockerised Dev Infrastructure"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "run" "/"  "Run Dev App + Dev Infrastructure (docker-compose with Postgres stack)"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "run_maria" "/"  "Run Dev App + Dockerised Dev Infrastructure (docker-compose with MariaDB stack)"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "runfull" "/"  "Run Dev App + Dockerised Dev Infrastructure fully Dockerised (docker-compose with Postgres stack)"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "runfull_maria" "/"  "Run Dev App + Dev Infrastructure fully Dockerised (docker-compose with MariaDB stack)"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "dev_localinfra_run" "/"  "Run Dev Infrastructure manually (docker-compose)"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "dev_localinfra_maria_run" "/"  "Run Dev Infrastructure manually (docker-compose)"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "dev_localinfra_stop" "/"  "Stop Dev Infrastructure manually when things gone stuck (docker-compose)"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "dev_localinfra_maria_stop" "/"  "Stop Dev Infrastructure manually when things gone stuck (docker-compose)"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "format_and_lint" "/"  "Format + lint (pre-commit style)"
	echo ""
	echo -e "${BOLD}🔥 Build, 🌬️  Publish and 🚀 Release: TODO${RESET}"
	echo ""
	echo -e "${BOLD}🧪 Tests: TODO${RESET}"
	echo ""
	echo -e "${BOLD}🧹 Housekeeping:${RESET}"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "format_and_lint" "/" "Run the formatter and linter our of pre-commit hooks"
	@printf "  %-20s %s %-20s %s %s\n" "[version_repo=X.Y.Z]" "/" "bump_version" "/" "Bump version + tag (use version_repo=X.Y.Z)"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "clean" "/" "Clean Python artifacts"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "coverageclean" "/" "Clean Coverage test artifacts"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "distclean" "/" "Clean Build and Dist artifacts"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "venvclean" "/" "Clean .venv artifacts"
	@printf "  %-20s %s %-20s %s %s\n" "[none]" "/" "nuke" "/" "Chain the cleaning steps above"
	echo ""
	echo -e "${GREEN}${BOLD}💡 Examples:${RESET}"
	echo "  make configure_repo_dev"
	echo "  make run"
	echo "  make database_init # on first install, after docker-compose has been spawned in DEV only !"
	echo "  make bump_version version_repo=1.2.3 tag_message=\"Release v1.2.3\""
	echo ""
	echo -e "${GREEN}${BOLD}📝 Default arguments that can be superseded on CLI:${RESET}"
	echo "- version_repo=\"0.0.0\""
	echo "-	tag_message=\"\""
	echo ""
	@printf "\033[0;32m%s\033[0m\n" "Run 'make help' anytime for this reference"