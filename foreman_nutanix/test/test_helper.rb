require 'minitest/autorun'

# Standalone: no Rails, no Foreman, no database. Only the plain-Ruby seam is
# loaded here. See test/README.md for what that rules out.
require 'foreman_nutanix/shim_client'
