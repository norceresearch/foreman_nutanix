require 'json'
require 'net/http'
require 'uri'

module ForemanNutanix
  # Single HTTP seam for every call the plugin makes to the nutanix-shim-server.
  #
  # Deliberately plain Ruby: no Rails, no ActiveSupport, no Rails.logger. It must
  # stay require-able from a bare minitest process with no Rails booted.
  #
  # Callers get back a Response value object rather than parsed data so that each
  # one keeps its own (and today wildly inconsistent) success/failure branching.
  class ShimClient
    DEFAULT_BASE_URL = 'http://localhost:8000'.freeze

    # Thin value object over a Net::HTTPResponse.
    class Response
      def initialize(raw)
        @raw = raw
      end

      def success?
        @raw.is_a?(Net::HTTPSuccess)
      end

      # Net::HTTPNoContent is the 204 response class. Exposed separately because
      # destroy_vm historically tested for it explicitly alongside success?.
      def no_content?
        @raw.is_a?(Net::HTTPNoContent)
      end

      def code
        @raw.code
      end

      def body
        @raw.body
      end

      # Intentionally does NOT rescue: a non-JSON body (an HTML 500 page, say)
      # must keep raising JSON::ParserError out to the caller, exactly as the
      # inline JSON.parse(response.body) calls did before.
      def json
        JSON.parse(body)
      end
    end

    def self.default_base_url
      ENV['NUTANIX_SHIM_SERVER_ADDR'] || DEFAULT_BASE_URL
    end

    # Strips the "prefix:" from identities of the form "ZXJnb24=:<uuid>".
    def self.normalize_uuid(uuid)
      uuid.to_s.include?(':') ? uuid.to_s.split(':').last : uuid.to_s
    end

    attr_reader :base_url

    # http: is an internal seam for tests only; production code never passes it.
    def initialize(base_url = nil, http: Net::HTTP)
      @base_url = (base_url || self.class.default_base_url).to_s.chomp('/')
      @http = http
    end

    def get(path)
      execute(Net::HTTP::Get, path)
    end

    def post(path, body = nil)
      execute(Net::HTTP::Post, path, body)
    end

    def delete(path)
      execute(Net::HTTP::Delete, path)
    end

    private

    def execute(verb_class, path, body = nil)
      uri = URI("#{@base_url}#{path}")
      connection = @http.new(uri.host, uri.port)
      connection.use_ssl = uri.scheme == 'https'

      request = verb_class.new(uri.request_uri)
      unless body.nil?
        request['Content-Type'] = 'application/json'
        request.body = body.to_json
      end

      Response.new(connection.request(request))
    end
  end
end
