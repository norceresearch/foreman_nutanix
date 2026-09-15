require 'test_helper'
require 'foreman_nutanix/gpu_profile'

# A profile as it arrives from the shim's /gpu-profiles endpoint.
def profile(overrides = {})
  {
    'ext_id' => '0005a1b2-1111-2222-3333-444455556666',
    'device_id' => 7864,
    'device_name' => 'Tesla T4',
    'vendor_name' => 'NVIDIA',
    'gpu_type' => 'PASSTHROUGH_GRAPHICS',
    'assignable' => 3,
    'is_in_use' => false,
  }.merge(overrides)
end

class GpuProfileUsableTest < Minitest::Test
  def test_a_complete_passthrough_profile_is_usable
    assert ForemanNutanix::GpuProfile.usable?(profile)
    assert ForemanNutanix::GpuProfile.usable?(profile('gpu_type' => 'PASSTHROUGH_COMPUTE'))
  end

  def test_virtual_profiles_are_not_usable
    # vGPU is rejected by the shim, so offering one would only let a user pick a
    # provision that cannot succeed.
    refute ForemanNutanix::GpuProfile.usable?(profile('gpu_type' => 'VIRTUAL'))
  end

  # Regression: a profile with a nil part still passed the PASSTHROUGH filter and
  # was offered in the dropdown. Selecting it posted a composite that parse
  # rejects, so the VM was created with NO GPU and the build reported success.
  def test_a_profile_missing_any_composite_part_is_not_usable
    refute ForemanNutanix::GpuProfile.usable?(profile('vendor_name' => nil))
    refute ForemanNutanix::GpuProfile.usable?(profile('device_id' => nil))
    refute ForemanNutanix::GpuProfile.usable?(profile('vendor_name' => '  '))
    refute ForemanNutanix::GpuProfile.usable?(profile('gpu_type' => nil))
  end

  def test_an_entirely_empty_profile_is_not_usable
    refute ForemanNutanix::GpuProfile.usable?({})
  end

  def test_every_usable_profile_round_trips_through_parse
    built = ForemanNutanix::GpuProfile.build(profile)
    assert_equal %w[7864 NVIDIA PASSTHROUGH_GRAPHICS], ForemanNutanix::GpuProfile.parse(built)
  end
end

class GpuProfileParseTest < Minitest::Test
  def parse(value)
    ForemanNutanix::GpuProfile.parse(value)
  end

  def test_a_well_formed_composite_yields_three_parts
    assert_equal %w[7864 NVIDIA PASSTHROUGH_GRAPHICS], parse('7864:NVIDIA:PASSTHROUGH_GRAPHICS')
  end

  def test_too_few_parts_are_rejected
    assert_nil parse('7864')
    assert_nil parse('7864:NVIDIA')
  end

  def test_blank_parts_are_rejected
    assert_nil parse('::')
    assert_nil parse('7864::PASSTHROUGH_GRAPHICS')
    assert_nil parse(':NVIDIA:PASSTHROUGH_GRAPHICS')
    assert_nil parse('7864:NVIDIA:')
  end

  def test_unselected_values_are_rejected
    assert_nil parse(nil)
    assert_nil parse('')
    assert_nil parse('   ')
  end

  def test_split_caps_at_three_so_gpu_type_is_never_truncated
    assert_equal %w[7864 NVIDIA A:B], parse('7864:NVIDIA:A:B')
  end
end

class GpuProfileLabelTest < Minitest::Test
  def label(overrides = {})
    ForemanNutanix::GpuProfile.label(profile(overrides))
  end

  def test_vendor_name_and_assignable_count
    assert_equal 'NVIDIA Tesla T4 (3 assignable)', label
  end

  def test_missing_assignable_drops_the_suffix
    assert_equal 'NVIDIA Tesla T4', label('assignable' => nil)
  end

  def test_missing_device_name_falls_back_to_the_device_id
    assert_equal 'NVIDIA (3 assignable)', label('device_name' => nil)
    assert_equal 'GPU 7864 (3 assignable)', label('device_name' => nil, 'vendor_name' => nil)
  end
end
