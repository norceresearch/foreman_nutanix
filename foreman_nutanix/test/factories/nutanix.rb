 FactoryBot.modify do
  factory :compute_resource do
    trait :nutanix do
      transient do
        cluster_id { 'test-cluster-uuid' }
      end
      provider { 'Nutanix' }
      url { cluster_id }
    end
  end
end
