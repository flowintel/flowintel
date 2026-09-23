# docker-bake.hcl
variable "BASE_IMAGE" { default = "ubuntu:noble" }
variable "NODE_VER" { default = "24.21.0" }
variable "PANDOC_VER" { default = "3.7.0.2" }
variable "PANDOC_PATCH" { default = "1" }
# Decision: Currently, we fix in Dockerfile to 3.4.0 version of the template for avoiding the migration to sourcesans.tty before Ubuntu/Debian are ready
# variable "EISVOGEL_VER" { default = "3.5.0" }

target "flowintel" {
  args = {
    BASE_IMAGE = BASE_IMAGE
    NODE_VER = NODE_VER
    PANDOC_VER  = PANDOC_VER
    PANDOC_PATCH  = PANDOC_PATCH
# Decision: Currently, we fix in Dockerfile to 3.4.0 version of the template for avoiding the migration to sourcesans.tty before Ubuntu/Debian are ready
#    EISVOGEL_VER = EISVOGEL_VER
  }
}