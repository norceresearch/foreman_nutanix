require 'test_google_helper'

module ForemanGoogle
  class GoogleComputeTest < GoogleTestCase
    let(:client) { mock('GoogleAdapter') }
    let(:zone) { 'zone-1' }
    let(:identity) { 'instance-id-or-name' }

    let(:instance) do
      nics = [OpenStruct.new(access_configs: [OpenStruct.new(nat_i_p: '1.2.3.4')], network: 'test/default', network_i_p: '10.10.10.23')]

      OpenStruct.new name: 'instance', network_interfaces: nics,
        creation_timestamp: Time.zone.now, zone: zone,
        machine_type: 'machineTypes/e2-micro'
    end

    subject { ForemanGoogle::GoogleCompute.new(client: client, zone: zone, identity: identity) }

    setup do
      client.stubs(:project_id).returns('project_id')
    end

    describe '#reload' do
      let(:zone) { 'http://test.org/fullurl/zones/zone-1' }
      let(:zone_name) { zone.split('/').last }

      it 'reloads the instance from gce and returns self' do
        client.expects(:instance).with(zone_name, identity).twice
        value(subject.reload).must_equal(subject)
      end
    end

    describe '#persisted?' do
      context 'with identity' do
        it 'is persisted' do
          client.stubs(:instance).with(zone, identity)
          value(subject).must_be(:persisted?)
        end
      end

      context 'without identity' do
        let(:identity) { nil }

        it 'is not persisted' do
          value(subject).wont_be(:persisted?)
        end
      end
    end

    describe '#ready?' do
      it 'is ready with running instance' do
        instance.status = 'RUNNING'
        client.expects(:instance).with(zone, identity).returns(instance)
        value(subject).must_be(:ready?)
      end

      it 'is not ready for not running instance' do
        instance.status = 'PROVISIONING'
        client.expects(:instance).with(zone, identity).returns(instance)
        value(subject).wont_be(:ready?)
      end
    end

    describe '#name & #hostname' do
      it 'default value' do
        args = { network: '' }
        cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: args)

        assert_includes cr.name, 'foreman-'
        assert_includes cr.hostname, 'foreman-'
      end

      it 'is parameterized' do
        args = { name: 'My new name' }
        cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: args)
        assert_includes cr.name, 'my-new-name'
        assert_includes cr.hostname, 'my-new-name'
      end
    end

    describe '#network_interfaces' do
      it 'with default value' do
        cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone)
        assert_includes cr.network_interfaces[0][:network], '/projects/project_id/global/networks/default'
      end

      it 'with custom value' do
        args = { network: 'custom' }
        cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: args)
        assert_includes cr.network_interfaces[0][:network], '/projects/project_id/global/networks/custom'
      end

      it 'with associated external ip' do
        args = { associate_external_ip: '1' }
        cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: args)
        expected_nics = [{ network: 'global/networks/default', access_configs: [{ name: 'External NAT', type: 'ONE_TO_ONE_NAT' }] }]

        assert_equal cr.network_interfaces, expected_nics
      end

      it 'with nics' do
        args = { associate_external_ip: '1', network_interfaces: [{ network: 'global/networks/custom' }] }
        cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: args)
        expected_nics = [{ network: 'global/networks/custom', access_configs: [{ name: 'External NAT', type: 'ONE_TO_ONE_NAT' }] }]

        assert_equal cr.network_interfaces, expected_nics
      end
    end

    describe '#volumes' do
      setup do
        client.stubs(:images).returns([OpenStruct.new(id: 1, name: 'coastal-image', self_link: 'test-self-link')])
        client.stubs(:image).returns(OpenStruct.new(id: 1, name: 'coastal-image', self_link: 'test-self-link'))
      end

      it 'no volumes' do
        cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone)
        volumes = [Google::Cloud::Compute::V1::AttachedDisk.new(disk_size_gb: 20)]

        assert_equal cr.volumes, volumes
      end

      it 'without image_id' do
        args = { volumes: [{ size_gb: '23' }] }
        cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: args)
        volume = cr.volumes.first

        assert_equal volume.device_name, "#{cr.name}-disk1"
        assert_empty volume.source
      end

      it 'with source_image' do
        args = { volumes: Array.new(2, { size_gb: '23', source_image: 'centos-stream-8-v20220317' }), image_id: '1' }
        cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: args)

        assert_equal cr.volumes[0].source, 'test-self-link'
        assert_equal cr.volumes[1].source, ''
      end
    end

    describe '#metadata' do
      let(:ssh_attrs) { { username: 'gce_user', public_key: 'public_key' } }

      it 'with user_data' do
        args = ssh_attrs.merge({ user_data: 'test' })
        cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: args)

        assert_includes cr.metadata[:items], { key: 'user-data', value: 'test' }
        assert_includes cr.metadata[:items], { key: 'ssh-keys', value: 'gce_user:public_key' }
      end

      it 'no user_data' do
        cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: ssh_attrs)
        assert_equal cr.metadata, { items: [{ key: 'ssh-keys', value: 'gce_user:public_key' }] }
      end
    end

    it '#pretty_machine_type - with instance' do
      cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, instance: instance)
      assert_equal cr.pretty_machine_type, 'e2-micro'
    end

    it '#pretty_machine_type - without instance' do
      args = { machine_type: 'high-cpu-16' }
      cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: args)
      assert_equal cr.pretty_machine_type, args[:machine_type]
    end

    it '#vm_ip_address' do
      cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, instance: instance)
      assert_equal cr.vm_ip_address, '1.2.3.4'
    end

    it '#private_ip_address' do
      cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, instance: instance)
      assert_equal cr.private_ip_address, '10.10.10.23'
    end

    it '#pretty_image_name' do
      client.stubs(:disk).returns(OpenStruct.new(source_image: '/path/to/centos-source-image'))
      instance.disks = [OpenStruct.new(source: 'path/to/foreman-disk1')]

      cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, instance: instance)
      assert_equal cr.pretty_image_name, 'centos-source-image'
    end

    it '@associate_external_ip' do
      cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone)
      assert_not cr.associate_external_ip

      cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: { associate_external_ip: '1' })
      assert cr.associate_external_ip
    end

    it '@network' do
      cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone)
      assert cr.network, 'default'

      cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, args: { network: 'my-network' })
      assert cr.network, 'my-network'
    end

    it '@zone' do
      cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone)
      assert zone, cr.zone
    end

    it '@zone_name' do
      cr = ForemanGoogle::GoogleCompute.new(client: client, zone: zone, instance: instance)
      assert zone, cr.zone_name
    end
  end
end
