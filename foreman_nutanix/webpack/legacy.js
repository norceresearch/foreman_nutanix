const jsonLoader = input => {
  const file = input.files[0];
  const reader = new FileReader();
  reader.onload = () => {
    const text = reader.result;
    const outputTextField = document.getElementById('gce_json');
    outputTextField.value = text;
  };
  reader.readAsText(file);
};

export const registerLegacy = () => {
  window.tfm = Object.assign(window.tfm || {}, {
    gce: { jsonLoader },
  });
};
