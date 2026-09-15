require 'minitest/autorun'

# Standalone: no Rails, no Foreman, no database. See test/README.md for what
# that rules out.
require 'foreman_nutanix/shim_client'

# NutanixCompute is a plain object, but it logs in nearly every method. This is
# the whole of the Rails surface the suite needs; it lives here rather than in
# one test file so a second file defining it cannot redefine the first's.
require 'logger'
module Rails
  def self.logger
    @logger ||= Logger.new(IO::NULL)
  end
end
