require 'test_helper'

require 'ostruct'
require_relative '../app/models/foreman_nutanix/nutanix_compute'

class NutanixComputeTest < Minitest::Test
  # Regression: ServersCollection#all builds VMs without a :gpus key, because
  # the shim's /list-vms payload has no gpus field. The VM index template calls
  # vm.gpus.empty? on every row, so a nil default raised NoMethodError there.
  def test_gpus_defaults_to_an_empty_array_when_absent
    vm = ForemanNutanix::NutanixCompute.new('cluster-1', name: 'vm1')
    assert_equal [], vm.gpus
    assert_empty vm.gpus
  end

  def test_gpus_passes_through_when_supplied
    vm = ForemanNutanix::NutanixCompute.new('cluster-1', name: 'vm1', gpus: %w[gpu-a gpu-b])
    assert_equal %w[gpu-a gpu-b], vm.gpus
    refute_empty vm.gpus
  end

  def test_gpus_explicit_nil_still_yields_an_empty_array
    vm = ForemanNutanix::NutanixCompute.new('cluster-1', name: 'vm1', gpus: nil)
    assert_equal [], vm.gpus
  end
end

class NutanixComputeGpuLabelsTest < Minitest::Test
  def build(gpus)
    ForemanNutanix::NutanixCompute.new('cluster-1', name: 'vm1', gpus: gpus)
  end

  def test_no_gpus_gives_no_labels
    assert_equal [], build(nil).gpu_labels
    assert_equal [], build([]).gpu_labels
  end

  def test_vendor_and_name_are_joined
    labels = build([{ 'vendor' => 'NVIDIA', 'name' => 'Tesla T4', 'device_id' => 7864 }]).gpu_labels
    assert_equal ['NVIDIA Tesla T4'], labels
  end

  def test_falls_back_to_device_id_when_name_is_missing_or_blank
    assert_equal ['NVIDIA 7864'], build([{ 'vendor' => 'NVIDIA', 'device_id' => 7864 }]).gpu_labels
    assert_equal ['NVIDIA 7864'], build([{ 'vendor' => 'NVIDIA', 'name' => '  ', 'device_id' => 7864 }]).gpu_labels
  end

  def test_name_alone_is_enough
    assert_equal ['Tesla T4'], build([{ 'name' => 'Tesla T4' }]).gpu_labels
  end

  def test_entirely_empty_gpu_still_gets_a_label
    assert_equal ['GPU'], build([{}]).gpu_labels
    assert_equal ['GPU'], build([{ 'vendor' => nil, 'name' => nil, 'device_id' => nil }]).gpu_labels
  end

  def test_label_count_always_matches_gpu_count
    labels = build([{ 'name' => 'A' }, {}, { 'vendor' => 'AMD' }]).gpu_labels
    assert_equal 3, labels.size
    refute_includes labels, ''
  end
end
