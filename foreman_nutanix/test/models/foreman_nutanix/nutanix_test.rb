require 'test_nutanix_helper'

module ForemanNutanix
  class NutanixTest < NutanixTestCase
    subject { ForemanNutanix::Nutanix.new(cluster: 'test-cluster') }
    let(:service) { mock('NutanixAdapter') }

    let(:instance_args) do
      nics = [OpenStruct.new(access_configs: [OpenStruct.new(nat_i_p: '1.2.3.4')], network: 'test/default', network_i_p: '10.10.10.23')]

      { name: "instance-#{Time.now.to_i}", network_interfaces: nics,
        creation_timestamp: Time.zone.now, zone: '/test/us-east1-b',
        machine_type: 'machineTypes/e2-micro' }
    end

    setup do
      subject.stubs(client: service)
      service.stubs(:project_id).returns('project_id')
    end

    describe '#find_vm_by_uuid' do
      it 'does query nutanix' do
        instance = OpenStruct.new(**instance_args)

        service.expects(:instance).with(subject.cluster, instance.name).returns(instance)

        compute = subject.find_vm_by_uuid(instance.name)
        value(compute).must_be_kind_of(ForemanNutanix::NutanixCompute)
      end

      it 'throws 404 when instance not found on Nutanix' do
        service
          .expects(:instance)
          .with(subject.cluster, 'non-existing-name-or-id')
          .raises(ActiveRecord::RecordNotFound)

        value { subject.find_vm_by_uuid('non-existing-name-or-id') }.must_raise(ActiveRecord::RecordNotFound)
      end
    end

    describe '#vms' do
      let(:instances) do
        Array.new(2) { |_i| OpenStruct.new(**instance_args) }
      end

      setup do
        service.expects(:instances).returns(instances)
      end

      it 'iteration over the vms array' do
        subject.vms.each_with_index { |instance, i| assert instance.name, instances[i].name }
      end

      it 'all method' do
        subject.vms.all.each_with_index { |instance, i| assert instance.name, instances[i].name }
      end
    end

    describe '#create_vm' do
      setup do
        service.expects(:image).returns(nil)
      end

      it 'without OS image' do
        value { subject.create_vm({ image_id: 0 }) }.must_raise(::Foreman::Exception)
      end
    end
  end
end
