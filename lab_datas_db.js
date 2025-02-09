
(function() {

    $(document).ready(function() {
  
      // initialize datetime pickers
      $('#datetimepicker1').datetimepicker({ format: 'd-m-Y H:i:s' });
      $('#datetimepicker2').datetimepicker({ format: 'd-m-Y H:i:s' });
  
      // auto-submit when node or range changes
      $('#node-select').change(function() {
        $("#data_selection").submit();
      });
      $('#range-select').change(function() {
        const range = $('#range-select').val();
        const now = new Date();
        const fromDate = new Date(now.getTime() - (range * 3600 * 1000));
        $("#datetimepicker1").val(formatDateDMY(fromDate));
        $("#datetimepicker2").val(formatDateDMY(now));
        $("#data_selection").submit();
      });
  
      // set hidden timezone before submit
      $("#data_selection").submit(function() {
        const tz = jstz.determine();
        $(".timezone").val(tz.name());
      });
  
      // set current range
      $("#range-select").val(range_time);
  
      // interval dropdown
      const intervalBtn = document.getElementById('interval-btn');
      const intervalDropdown = document.getElementById('interval-dropdown');
      intervalBtn.addEventListener('click', function() {
        if (intervalDropdown.style.display === 'none' || intervalDropdown.style.display === '') {
          intervalDropdown.style.display = 'block';
        } else {
          intervalDropdown.style.display = 'none';
        }
      });
      const options = intervalDropdown.querySelectorAll('div[data-value]');
      options.forEach(function(opt) {
        opt.addEventListener('click', function() {
          const val = this.getAttribute('data-value');
          intervalBtn.textContent = "Intervale " + val;
          intervalDropdown.style.display = 'none';
          $.post("/update_cron", { interval: val })
          .done(function(response) {
            console.log("cron updated with interval:", response.selected_interval);
          })
          .fail(function() {
            console.log("error updating cron");
          });
        });
      });
  
      // live button
      $('#btn-live').click(function() {
        window.location.href = "/lab_datas?node=" + node;
      });
  
      // plotly button
      let plotlyLink = null;
      $('#btn-plotly').click(function() {
        const btnPlotly = this;
        if (plotlyLink) {
          window.open(plotlyLink, "_blank");
          return;
        }
        btnPlotly.classList.add('clicked');
        btnPlotly.textContent = "...envoie";
        $.get("/to_plotly", {
          from: start_date,
          to: end_date,
          timezone: timezone,
          node: node
        })
        .done(function(data) {
          plotlyLink = data;
          btnPlotly.textContent = "Afficher";
          btnPlotly.classList.remove('clicked');
        })
        .fail(function() {
          btnPlotly.textContent = "Erreur";
          btnPlotly.classList.remove('clicked');
        });
      });
  
      // theme toggle
      $('#btn-mode').click(function() {
        darkMode = !darkMode;
        if (darkMode) {
          document.body.classList.add('dark-mode');
        } else {
          document.body.classList.remove('dark-mode');
        }
        localStorage.setItem('darkMode', darkMode);
        drawAllCharts();
      });
  
      // digital clock
      setInterval(currentTime, 1000);
      currentTime();
  
      // initialize chrono
      initChrono();
  
      // init gauges once dom content loaded
      initGauges();
    }); // end document ready
  
  
    // function to format date dd-mm-yyyy hh:mm:ss
    function formatDateDMY(date) {
      const day = String(date.getDate()).padStart(2, '0');
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const year = date.getFullYear();
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      return `${day}-${month}-${year} ${hours}:${minutes}:${seconds}`;
    }
  
    // current time display
    function currentTime() {
      const date = new Date();
      const day = date.getDay();
      let hour = date.getHours();
      let min = date.getMinutes();
      let sec = date.getSeconds();
      const month = date.getMonth();
      let currDate = date.getDate();
      const year = date.getFullYear();
  
      const jours = ["DIM","LUN","MAR","MER","JEU","VEN","SAM"];
      const mois = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
        "Août", "Septembre", "Octobre", "Novembre", "Décembre"
      ];
  
      hour = updateTime(hour);
      min = updateTime(min);
      sec = updateTime(sec);
      currDate = updateTime(currDate);
  
      $("#time").html(`${hour}:${min}`);
      $("#sec").html(`${sec}`);
      $("#med").html("");
      $("#full-date").html(`${currDate} ${mois[month]} ${year}`);
  
      const showDay = $(".dayDiv span");
      showDay.css("opacity", "0.4");
      showDay.eq(day).css("opacity", "1");
      showDay.eq(day).text(jours[day]);
    }
  
    function updateTime(x) {
      return x < 10 ? "0" + x : x;
    }
  
    // chrono and timer logic
    function initChrono() {
      let mode = "chrono";
      let timerInterval = null;
      let totalSeconds = 0;
      let timerDuration = 30 * 60;
      let running = false;
  
      $("#switch-mode").click(function() {
        resetTimer();
        mode = (mode === "chrono") ? "timer" : "chrono";
        if (mode === "timer") {
          setEditable(true);
          $("#chrono-timer-display").html("00:30:00");
        } else {
          setEditable(false);
          $("#chrono-timer-display").html("00:00:00");
        }
        updateDisplay();
      });
  
      $("#start-button").click(function() {
        if (!running) {
          if (mode === "timer") {
            const val = $("#chrono-timer-display").text().trim();
            const sec = timeToSeconds(val);
            timerDuration = sec > 0 ? sec : 1800;
            totalSeconds = 0;
          }
          startTimer();
        } else {
          stopTimer();
        }
      });
  
      $("#reset-button").click(function() {
        resetTimer();
      });
  
      function startTimer() {
        stopTimer();
        running = true;
        timerInterval = setInterval(() => {
          totalSeconds++;
          if (mode === "timer" && totalSeconds >= timerDuration) {
            stopTimer();
          }
          updateDisplay();
        }, 1000);
        updateDisplay();
      }
  
      function stopTimer() {
        clearInterval(timerInterval);
        timerInterval = null;
        running = false;
        updateDisplay();
      }
  
      function resetTimer() {
        stopTimer();
        totalSeconds = 0;
        if (mode === "timer") {
          timerDuration = 1800;
          $("#chrono-timer-display").html(formatTime(timerDuration));
        } else {
          $("#chrono-timer-display").html("00:00:00");
        }
        updateDisplay();
      }
  
      function updateDisplay() {
        if (mode === "chrono") {
          $("#chrono-timer-display").html(formatTime(totalSeconds));
        } else {
          const remaining = timerDuration - totalSeconds;
          $("#chrono-timer-display").html(formatTime(Math.max(remaining, 0)));
        }
        if (mode === "chrono") {
          $("#switch-mode").text("Minuteur");
        } else {
          $("#switch-mode").text("Chrono");
        }
        if (running) {
          $("#start-button").text("Stop");
        } else {
          $("#start-button").text("Start");
        }
      }
  
      function setEditable(isEditable) {
        $("#chrono-timer-display").attr("contenteditable", isEditable);
      }
  
      function formatTime(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
      }
  
      function timeToSeconds(timeStr) {
        const parts = timeStr.split(":").map(Number);
        let sec = 0;
        if (parts.length === 3) {
          sec = parts[0]*3600 + parts[1]*60 + parts[2];
        } else if (parts.length === 2) {
          sec = parts[0]*60 + parts[1];
        } else if (parts.length === 1) {
          sec = parts[0];
        }
        return sec;
      }
  
      setEditable(false);
      updateDisplay();
    }
  
    // redraw charts when theme changes
    function drawAllCharts() {
      createTempChart();
      createHumChart();
      createPressChart();
      initGauges();
    }
  
    // gauges
    function initGauges() {
      const tempOpts = getGaugeOptions('temp', darkMode);
      const gaugeTemp = new Gauge(document.getElementById("gauge_temp")).setOptions(tempOpts);
      gaugeTemp.maxValue = 40;
      gaugeTemp.setMinValue(0);
      gaugeTemp.animationSpeed = 32;
      gaugeTemp.set(currentTemp);
      document.getElementById("temp-value").textContent = currentTemp.toFixed(1) + " °C";
  
      const humOpts = getGaugeOptions('hum', darkMode);
      const gaugeHum = new Gauge(document.getElementById("gauge_hum")).setOptions(humOpts);
      gaugeHum.maxValue = 100;
      gaugeHum.setMinValue(0);
      gaugeHum.animationSpeed = 32;
      gaugeHum.set(currentHum);
      document.getElementById("hum-value").textContent = currentHum.toFixed(1) + " %";
  
      const pressOpts = getGaugeOptions('press', darkMode);
      const gaugePress = new Gauge(document.getElementById("gauge_press")).setOptions(pressOpts);
      gaugePress.maxValue = 1100;
      gaugePress.setMinValue(900);
      gaugePress.animationSpeed = 32;
      gaugePress.set(currentPress);
      document.getElementById("press-value").textContent = currentPress.toFixed(2) + " hPa";
    }
  
    // gauge style
    function getGaugeOptions(type, isDarkMode) {
      let staticZones, staticLabels;
      const labelColor = isDarkMode ? "#ffffff" : "#000000";
      const pointerColor = isDarkMode ? "#ffffff" : "#000000";
  
      if (type === 'temp') {
        staticZones = [
          { strokeStyle: "rgba(244,67,54,0.8)", min: 10, max: 13 },
          { strokeStyle: "rgba(255,193,7,0.8)", min: 13, max: 17 },
          { strokeStyle: "rgba(76,175,80,0.8)", min: 17, max: 23 },
          { strokeStyle: "rgba(255,193,7,0.8)", min: 23, max: 30 },
          { strokeStyle: "rgba(244,67,54,0.8)", min: 30, max: 35 }
        ];
        staticLabels = {
          font: "12px sans-serif",
          labels: [10,13,17,23,30,35],
          color: labelColor,
          fractionDigits: 0
        };
      } else if (type === 'hum') {
        staticZones = [
          { strokeStyle: "rgba(244,67,54,0.8)", min: 20, max: 25 },
          { strokeStyle: "rgba(255,193,7,0.8)", min: 25, max: 40 },
          { strokeStyle: "rgba(76,175,80,0.8)", min: 40, max: 60 },
          { strokeStyle: "rgba(255,193,7,0.8)", min: 60, max: 80 },
          { strokeStyle: "rgba(244,67,54,0.8)", min: 80, max: 85 }
        ];
        staticLabels = {
          font: "12px sans-serif",
          labels: [20,25,40,60,80,85],
          color: labelColor,
          fractionDigits: 0
        };
      } else if (type === 'press') {
        staticZones = [
          { strokeStyle: "rgba(244,67,54,0.8)", min: 955, max: 960 },
          { strokeStyle: "rgba(255,193,7,0.8)", min: 960, max: 990 },
          { strokeStyle: "rgba(76,175,80,0.8)", min: 990, max: 1030 },
          { strokeStyle: "rgba(255,193,7,0.8)", min: 1030, max: 1070 },
          { strokeStyle: "rgba(244,67,54,0.8)", min: 1070, max: 1075 }
        ];
        staticLabels = {
          font: "12px sans-serif",
          labels: [955,990,1030,1075],
          color: labelColor,
          fractionDigits: 0
        };
      }
  
      return {
        angle: -0.6,
        lineWidth: 0.2,
        radiusScale: 0.8,
        pointer: {
          length: 0.6,
          strokeWidth: 0.035,
          color: pointerColor
        },
        limitMax: false,
        limitMin: false,
        highDpiSupport: true,
        staticZones: staticZones,
        staticLabels: staticLabels
      };
    }
  
  })();
  
