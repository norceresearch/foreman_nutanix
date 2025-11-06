ForemanNutanix::Engine.routes.draw do
  # No plugin-specific routes needed
end

Rails.application.routes.draw do
  # Define the gce resource route to create the gce_path helper
  # This is needed because the compute resource model is named GCE
  scope :foreman_nutanix do
    # Create a dummy route that generates the gce_path helper
    get 'gce/:id', to: redirect('/compute_resources/%{id}'), as: :gce
  end
end
