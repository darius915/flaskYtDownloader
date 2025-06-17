document.getElementById('download-form').addEventListener('submit', function(e) {
  e.preventDefault();
  const formData = new FormData(this);
  fetch('/download', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    const id = data.id;
    const interval = setInterval(() => {
      fetch('/progress/' + id)
        .then(res => res.json())
        .then(progress => {
          document.getElementById('status').textContent = 'Progress: ' + progress.progress;
          if (progress.progress.includes('100%')) clearInterval(interval);
        });
    }, 1000);
  });
});
