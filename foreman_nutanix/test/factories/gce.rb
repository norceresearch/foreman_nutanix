FactoryBot.modify do
  factory :compute_resource do
    trait :google_gce do
      transient do
        project_id { 'coastal-haven-123456' }
      end
      provider { 'GCE' }
      password do
        # instead of private_key, we hand size of new key to generate
        # this generate valid mocked key, due to overload of OpenSSL::PKey::RSA.new
        <<-END_AUTHTOKEN
        {
          "type": "service_account",
          "project_id": "#{project_id}",
          "private_key_id": "7b1afc23bdfd510c49d827f3151fac94b089b42b",
          "private_key": 2048,
          "client_email": "xxxxxxx-compute@developer.gserviceaccount.com",
          "client_id": "111235611116543210000",
          "auth_uri": "https://accounts.google.com/o/oauth2/auth",
          "token_uri": "https://oauth2.googleapis.com/token",
          "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
          "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/552404852006-compute%40developer.gserviceaccount.com"
        }
        END_AUTHTOKEN
      end
    end
  end
end
