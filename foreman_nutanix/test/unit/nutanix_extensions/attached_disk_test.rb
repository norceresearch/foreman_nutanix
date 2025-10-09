require 'test_google_helper'

module GoogleExtensions
  class AttachedDiskTest < GoogleTestCase
    describe 'insert_attrs' do
      it 'with source image' do
        disk = Google::Cloud::Compute::V1::AttachedDisk.new(source: 'source-image')
        assert_equal 'source-image', disk.insert_attrs[:source_image]
      end

      it 'without source image' do
        disk = Google::Cloud::Compute::V1::AttachedDisk.new
        assert_empty disk.insert_attrs[:source_image]
      end
    end
  end
end
