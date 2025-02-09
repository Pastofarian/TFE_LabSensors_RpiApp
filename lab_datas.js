
(function() {

    // apply dark mode 
    let darkMode = (localStorage.getItem('darkMode') === 'true');
    if (darkMode) {
      document.body.classList.add('dark-mode');
    }
  
    // dark/light button
    const btnMode = document.getElementById('btn-mode');
    btnMode.addEventListener('click', function() {
      darkMode = !darkMode;
      if (darkMode) {
        document.body.classList.add('dark-mode');
      } else {
        document.body.classList.remove('dark-mode');
      }
      localStorage.setItem('darkMode', darkMode);
    });
  
    // auto-refresh sensor data every 10s
    function updateLiveData() {
      // fetch from /live_data?node=1 as example
      fetch("/live_data?node=1")
        .then(resp => resp.json())
        .then(json => {
          // update dom if you have dedicated ids
          const tempEl = document.getElementById("tempValue");
          const humEl = document.getElementById("humValue");
          const presEl = document.getElementById("presValue");
  
          if (tempEl) {
            tempEl.innerText = json.temp ? json.temp.toFixed(1) + " °C" : "N/A";
          }
          if (humEl) {
            humEl.innerText = json.hum ? json.hum.toFixed(1) + " %" : "N/A";
          }
          if (presEl) {
            presEl.innerText = json.pres ? json.pres.toFixed(1) + " Pa" : "N/A";
          }
        })
        .catch(err => console.log("error fetching live data:", err));
    }
  
    // set 10s interval
    setInterval(updateLiveData, 10000);
  
    // update once on load
    updateLiveData();
  
    // node selection form
    $(document).ready(function() {
      $('#node-select').change(function() {
        $('#cellule_selection').submit();
      });
    });
  
  })();
  
