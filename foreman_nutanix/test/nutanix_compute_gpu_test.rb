require 'test_helper'

require 'ostruct'
require_relative '../app/models/foreman_nutanix/nutanix_compute'

class NutanixComputeGpuAccessorsTest < Minitest::Test
  def build(attrs = {})
    ForemanNutanix::NutanixCompute.new('cluster-1', { name: 'vm1' }.merge(attrs))
  end

  def test_gpu_composite_comes_from_args
    assert_equal '7864:NVIDIA:PASSTHROUGH_GRAPHICS',
      build(gpu: '7864:NVIDIA:PASSTHROUGH_GRAPHICS').gpu
  end

  def test_gpu_defaults_to_nil
    assert_nil build.gpu
  end

  def test_gpu_count_comes_from_args
    assert_equal 4, build(gpu_count: 4).gpu_count
  end

  def test_gpu_count_defaults_to_nil
    assert_nil build.gpu_count
  end

  def test_gpu_and_gpu_count_are_writable
    vm = build
    vm.gpu = '7864:NVIDIA:PASSTHROUGH_COMPUTE'
    vm.gpu_count = 2
    assert_equal '7864:NVIDIA:PASSTHROUGH_COMPUTE', vm.gpu
    assert_equal 2, vm.gpu_count
  end
end

# #save posts the provision request through the private #shim memo. Seed that
# memo with a recorder instead of reaching for the network; ShimClient itself is
# covered separately in shim_client_test.rb.
class FakeShimResponse
  def success?
    true
  end

  def json
    { 'ext_id' => 'vm-ext-1' }
  end

  def code
    '200'
  end

  def body
    '{}'
  end
end

class RecordingShim
  attr_reader :path, :payload

  def post(path, payload = nil)
    @path = path
    @payload = payload
    FakeShimResponse.new
  end
end

module GpuProvisionHelper
  # A provision that supplies everything #save demands and nothing more.
  BASE_ATTRS = {
    name: 'vm1',
    subnet_ext_id: 'subnet-1',
    storage_container_ext_id: 'sc-1',
    memory: 4,
    disk_size_gb: 50,
  }.freeze

  # Exactly what the plugin posted before GPU support existed. Any drift here is
  # a regression: a GPU-less provision must stay byte-identical.
  PRE_GPU_PAYLOAD = {
    name: 'vm1',
    cluster_ext_id: 'cluster-1',
    subnet_ext_id: 'subnet-1',
    storage_container_ext_id: 'sc-1',
    num_sockets: 1,
    num_cores_per_socket: 2,
    memory_size_bytes: 4_294_967_296,
    disk_size_bytes: 53_687_091_200,
    description: '',
    secure_boot: nil,
    boot_method: nil,
  }.freeze

  GPU_KEYS = %i[gpu_device_id gpu_vendor gpu_mode gpu_count].freeze

  def provision(attrs = {})
    vm = ForemanNutanix::NutanixCompute.new('cluster-1', BASE_ATTRS.merge(attrs))
    shim = RecordingShim.new
    vm.instance_variable_set(:@shim, shim)
    vm.save
    shim.payload
  end

end

class NutanixComputeGpuPayloadTest < Minitest::Test
  include GpuProvisionHelper

  def test_no_gpu_selected_leaves_the_payload_exactly_as_it_was
    assert_equal PRE_GPU_PAYLOAD, provision
    assert_equal PRE_GPU_PAYLOAD.keys, provision.keys
  end

  def test_no_gpu_selected_adds_no_gpu_keys
    payload = provision
    GPU_KEYS.each { |key| refute_includes payload.keys, key }
  end

  def test_well_formed_composite_is_split_into_three_fields
    payload = provision(gpu: '7864:NVIDIA:PASSTHROUGH_GRAPHICS')
    assert_equal 7864, payload[:gpu_device_id]
    assert_equal 'NVIDIA', payload[:gpu_vendor]
    assert_equal 'PASSTHROUGH_GRAPHICS', payload[:gpu_mode]
  end

  def test_selecting_a_gpu_leaves_every_other_key_untouched
    payload = provision(gpu: '7864:NVIDIA:PASSTHROUGH_GRAPHICS')
    assert_equal PRE_GPU_PAYLOAD, payload.reject { |key, _| GPU_KEYS.include?(key) }
  end
end

class NutanixComputeGpuCountTest < Minitest::Test
  include GpuProvisionHelper

  GPU = '7864:NVIDIA:PASSTHROUGH_GRAPHICS'.freeze

  def test_count_defaults_to_one_when_a_gpu_is_selected_without_one
    assert_equal 1, provision(gpu: GPU)[:gpu_count]
  end

  def test_count_defaults_to_one_when_the_hidden_field_posts_empty
    assert_equal 1, provision(gpu: GPU, gpu_count: '')[:gpu_count]
    assert_equal 1, provision(gpu: GPU, gpu_count: nil)[:gpu_count]
  end

  def test_an_explicit_count_is_carried_through
    assert_equal 3, provision(gpu: GPU, gpu_count: 3)[:gpu_count]
  end

  def test_a_string_count_from_the_form_is_coerced
    assert_equal 3, provision(gpu: GPU, gpu_count: '3')[:gpu_count]
  end

  def test_a_nonsensical_count_still_provisions_the_selected_gpu
    assert_equal 1, provision(gpu: GPU, gpu_count: 0)[:gpu_count]
    assert_equal 1, provision(gpu: GPU, gpu_count: -2)[:gpu_count]
  end
end

class NutanixComputeMalformedGpuCompositeTest < Minitest::Test
  include GpuProvisionHelper

  # A composite that did not survive the round trip must omit the GPU entirely.
  # Provisioning against half a GPU spec is worse than provisioning without one.
  def assert_no_gpu_fields(gpu)
    payload = provision(gpu: gpu)
    GPU_KEYS.each do |key|
      refute_includes payload.keys, key, "expected #{gpu.inspect} to contribute no #{key}"
    end
    assert_equal PRE_GPU_PAYLOAD, payload
  end

  # Unselected: no GPU fields, no error. This is what an untouched dropdown posts.
  def test_unselected_values_contribute_no_gpu_fields
    assert_no_gpu_fields ''
    assert_no_gpu_fields '   '
    assert_no_gpu_fields nil
  end

  # Selected but malformed: raise. Silently building a GPU-less VM and reporting
  # success is the worst available outcome, and matches how a missing network or
  # storage container already behaves in #save.
  def assert_raises_on(gpu)
    error = assert_raises(StandardError) { provision(gpu: gpu) }
    assert_match(/Malformed GPU selection/, error.message)
  end

  def test_too_few_parts_raise
    assert_raises_on '7864'
    assert_raises_on '7864:NVIDIA'
  end

  def test_blank_parts_raise
    assert_raises_on '::'
    assert_raises_on '7864::PASSTHROUGH_GRAPHICS'
    assert_raises_on ':NVIDIA:PASSTHROUGH_GRAPHICS'
    assert_raises_on '7864:NVIDIA:'
  end

  # split(':', 3) caps at three, so a gpu_type is never truncated by a stray
  # colon further right.
  def test_extra_colons_stay_with_the_gpu_type
    payload = provision(gpu: '7864:NVIDIA:PASSTHROUGH_GRAPHICS:EXTRA')
    assert_equal 'PASSTHROUGH_GRAPHICS:EXTRA', payload[:gpu_mode]
    assert_equal 'NVIDIA', payload[:gpu_vendor]
  end
end
