require 'test_helper'

class ShimClientTest < Minitest::Test
  # --- Fakes injected through the http: keyword -----------------------------

  # Stands in for a Net::HTTP connection object.
  class FakeConnection
    attr_reader :host, :port, :requests
    attr_accessor :use_ssl

    def initialize(host, port, response)
      @host = host
      @port = port
      @response = response
      @requests = []
      @use_ssl = nil
    end

    def request(req)
      @requests << req
      @response
    end
  end

  # Stands in for the Net::HTTP class itself.
  class FakeHttp
    attr_reader :connections

    def initialize(response)
      @response = response
      @connections = []
    end

    def new(host, port)
      conn = FakeConnection.new(host, port, @response)
      @connections << conn
      conn
    end

    def last_connection
      @connections.last
    end

    def last_request
      last_connection.requests.last
    end
  end

  def stub_response(klass = Net::HTTPOK, code: '200', body: '{}')
    response = klass.new('1.1', code, 'Stub')
    response.instance_variable_set(:@body, body)
    response.instance_variable_set(:@read, true)
    response
  end

  def client(base_url = 'http://shim.example:8000', response: stub_response)
    http = FakeHttp.new(response)
    [ForemanNutanix::ShimClient.new(base_url, http: http), http]
  end

  def with_env(value)
    previous = ENV['NUTANIX_SHIM_SERVER_ADDR']
    had_key = ENV.key?('NUTANIX_SHIM_SERVER_ADDR')
    if value.nil?
      ENV.delete('NUTANIX_SHIM_SERVER_ADDR')
    else
      ENV['NUTANIX_SHIM_SERVER_ADDR'] = value
    end
    yield
  ensure
    if had_key
      ENV['NUTANIX_SHIM_SERVER_ADDR'] = previous
    else
      ENV.delete('NUTANIX_SHIM_SERVER_ADDR')
    end
  end

  # --- Base URL -------------------------------------------------------------

  def test_base_url_defaults_to_localhost_when_env_is_unset
    with_env(nil) do
      assert_equal 'http://localhost:8000', ForemanNutanix::ShimClient.new.base_url
      assert_equal 'http://localhost:8000', ForemanNutanix::ShimClient.default_base_url
    end
  end

  def test_base_url_comes_from_env_when_set
    with_env('http://shim.internal:9000') do
      assert_equal 'http://shim.internal:9000', ForemanNutanix::ShimClient.new.base_url
      assert_equal 'http://shim.internal:9000', ForemanNutanix::ShimClient.default_base_url
    end
  end

  def test_explicit_base_url_wins_over_env
    with_env('http://shim.internal:9000') do
      assert_equal 'http://explicit:1234', ForemanNutanix::ShimClient.new('http://explicit:1234').base_url
    end
  end

  def test_trailing_slash_is_chomped
    shim = ForemanNutanix::ShimClient.new('http://shim.example:8000/')
    assert_equal 'http://shim.example:8000', shim.base_url
  end

  def test_trailing_slash_from_env_is_chomped
    with_env('http://shim.internal:9000/') do
      assert_equal 'http://shim.internal:9000', ForemanNutanix::ShimClient.new.base_url
    end
  end

  # --- Verbs and path construction -----------------------------------------

  def test_get_builds_a_get_request_at_the_joined_path
    shim, http = client
    shim.get('/api/v1/vmm/list-images')

    request = http.last_request
    assert_instance_of Net::HTTP::Get, request
    assert_equal '/api/v1/vmm/list-images', request.path
    assert_equal 'shim.example', http.last_connection.host
    assert_equal 8000, http.last_connection.port
  end

  def test_post_builds_a_post_request_at_the_joined_path
    shim, http = client
    shim.post('/api/v1/vmm/vms/abc/power-state', { action: 'POWER_ON' })

    assert_instance_of Net::HTTP::Post, http.last_request
    assert_equal '/api/v1/vmm/vms/abc/power-state', http.last_request.path
  end

  def test_delete_builds_a_delete_request_at_the_joined_path
    shim, http = client
    shim.delete('/api/v1/vmm/vms/abc')

    assert_instance_of Net::HTTP::Delete, http.last_request
    assert_equal '/api/v1/vmm/vms/abc', http.last_request.path
  end

  def test_path_is_joined_to_a_base_url_that_had_a_trailing_slash
    http = FakeHttp.new(stub_response)
    ForemanNutanix::ShimClient.new('http://shim.example:8000/', http: http).get('/api/v1/vmm/list-vms')

    assert_equal '/api/v1/vmm/list-vms', http.last_request.path
  end

  # --- Body encoding --------------------------------------------------------

  def test_post_json_encodes_the_body_and_sets_content_type
    shim, http = client
    shim.post('/api/v1/vmm/provision-vm', { name: 'vm-1', num_sockets: 2 })

    assert_equal 'application/json', http.last_request['Content-Type']
    assert_equal({ 'name' => 'vm-1', 'num_sockets' => 2 }, JSON.parse(http.last_request.body))
  end

  def test_post_without_a_body_sends_no_body_and_no_content_type
    shim, http = client
    shim.post('/api/v1/vmm/noop')

    assert_nil http.last_request.body
    assert_nil http.last_request['Content-Type']
  end

  def test_get_sends_no_body_and_no_content_type
    shim, http = client
    shim.get('/api/v1/vmm/list-vms')

    assert_nil http.last_request.body
    assert_nil http.last_request['Content-Type']
  end

  # --- Scheme ---------------------------------------------------------------

  def test_https_is_inferred_from_the_scheme
    http = FakeHttp.new(stub_response)
    ForemanNutanix::ShimClient.new('https://shim.example', http: http).get('/api/v1/vmm/list-vms')

    assert_equal true, http.last_connection.use_ssl
    assert_equal 443, http.last_connection.port
  end

  def test_http_scheme_does_not_enable_ssl
    shim, http = client
    shim.get('/api/v1/vmm/list-vms')

    assert_equal false, http.last_connection.use_ssl
  end

  # --- Response -------------------------------------------------------------

  def test_success_is_true_for_200
    shim, = client(response: stub_response(Net::HTTPOK, code: '200'))
    response = shim.get('/whatever')

    assert_equal true, response.success?
    assert_equal '200', response.code
  end

  def test_success_is_false_for_404
    shim, = client(response: stub_response(Net::HTTPNotFound, code: '404', body: 'not found'))
    response = shim.get('/whatever')

    assert_equal false, response.success?
    assert_equal '404', response.code
    assert_equal 'not found', response.body
  end

  def test_success_is_false_for_500
    error = stub_response(Net::HTTPInternalServerError, code: '500', body: '<html>boom</html>')
    shim, = client(response: error)
    response = shim.get('/whatever')

    assert_equal false, response.success?
    assert_equal '500', response.code
  end

  def test_no_content_is_true_only_for_204
    shim, = client(response: stub_response(Net::HTTPNoContent, code: '204', body: nil))
    assert_equal true, shim.get('/whatever').no_content?

    shim_ok, = client(response: stub_response(Net::HTTPOK, code: '200'))
    assert_equal false, shim_ok.get('/whatever').no_content?
  end

  def test_json_parses_the_body
    shim, = client(response: stub_response(Net::HTTPOK, body: '[{"ext_id":"abc"}]'))

    assert_equal [{ 'ext_id' => 'abc' }], shim.get('/whatever').json
  end

  def test_json_propagates_parser_error_on_non_json_bodies
    error = stub_response(Net::HTTPInternalServerError, code: '500', body: '<html>boom</html>')
    shim, = client(response: error)

    assert_raises(JSON::ParserError) { shim.get('/whatever').json }
  end

  # --- normalize_uuid -------------------------------------------------------

  def test_normalize_uuid_strips_a_prefix
    assert_equal 'the-uuid', ForemanNutanix::ShimClient.normalize_uuid('ZXJnb24=:the-uuid')
  end

  def test_normalize_uuid_leaves_a_bare_uuid_alone
    assert_equal 'the-uuid', ForemanNutanix::ShimClient.normalize_uuid('the-uuid')
  end

  def test_normalize_uuid_coerces_non_strings
    assert_equal '', ForemanNutanix::ShimClient.normalize_uuid(nil)
    assert_equal '42', ForemanNutanix::ShimClient.normalize_uuid(42)
  end

  def test_normalize_uuid_keeps_only_the_last_segment
    assert_equal 'c', ForemanNutanix::ShimClient.normalize_uuid('a:b:c')
  end
end
