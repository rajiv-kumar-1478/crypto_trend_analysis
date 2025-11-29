document.addEventListener('DOMContentLoaded', () => {
    const coinDropdown = document.getElementById('coinDropdown');
    const daysDropdown = document.getElementById('daysDropdown');
    coinDropdown.value = 'Bitcoin'; // default to Bitcoin
    daysDropdown.value = '180';     // default to Last 6 Months (value="180")
    const sentimentLineChart = document.getElementById('sentimentLineChart');
    const sentimentBarChart = document.getElementById('sentimentBarChart');
    const sentimentOverlayChart = document.getElementById('sentimentOverlayChart');
    const wordcloudDiv = document.getElementById('wordcloud');
  
    const correlationEl = document.getElementById('correlation');
    const dirAccuracyEl = document.getElementById('directionalAccuracy');
  
    const sentimentLineChartInstance = new Chart(sentimentLineChart, {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: 'Sentiment Score',
            data: [],
            borderColor: '#4fd1c5',
            fill: false,
            tension: 0.1
          }]
        },
        options: {
          scales: {
            x: {
              ticks: {
                color: 'rgb(255, 255, 255)' // X-axis
              }
            },
            y: {
              ticks: {
                color: 'rgb(255, 255, 255)' // Y-axis
              }
            }
          }
        }
      });
      
  
    const sentimentBarChartInstance = new Chart(sentimentBarChart, {
        type: 'bar',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Positive',
              data: [],
              backgroundColor: '#4fd1c5',
            },
            {
              label: 'Negative',
              data: [],
              backgroundColor: '#fc8181',
            },
            {
              label: 'Neutral',
              data: [],
              backgroundColor: '#fbbf24',
            }
          ]
        },
        options: {
          scales: {
            x: {
              ticks: {
                color: 'rgb(255, 255, 255)'  //  X-axis label color
              }
            },
            y: {
              ticks: {
                color: 'rgb(255, 255, 255)'  //  Y-axis label color (optional)
              }
            }
          }
        }
      });
      
  
      // 
      const sentimentOverlayChartInstance = new Chart(sentimentOverlayChart, {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Sentiment Score',
              data: [],
              borderColor: '#4fd1c5',
              fill: false,
              tension: 0.1,
              yAxisID: 'y'
            },
            {
              label: 'Price Change (Normalized)',
              data: [],
              borderColor: '#fbbf24',
              fill: false,
              tension: 0.1,
              yAxisID: 'y1'
            }
          ]
        },
        options: {
          responsive: true,
          interaction: {
            mode: 'index',
            intersect: false
          },
          scales: {
            x: {
              ticks: {
                color: 'rgb(255, 255, 255)'
              }
            },
            y: {
              position: 'left',
              min: -1,
              max: 1,
              title: {
                display: true,
                text: 'Sentiment Score',
                color: 'white'
              },
              ticks: {
                color: 'rgb(255, 255, 255)'
              }
            },
            y1: {
              position: 'right',
              min: -1,
              max: 1,
              grid: {
                drawOnChartArea: false
              },
              title: {
                display: true,
                text: 'Price Change (Normalized)',
                color: 'white'
              },
              ticks: {
                color: 'rgb(255, 255, 255)'
              }
            }
          },
          plugins: {
            tooltip: {
              mode: 'index',
              intersect: false,
              callbacks: {
                label: function(context) {
                  return `${context.dataset.label}: ${context.parsed.y}`;
                }
              }
            }
          }
        }
      });
      
  
    const fetchData = () => {
      const coin = coinDropdown.value.toLowerCase();
      const days = daysDropdown.value;
  
      // Fetch sentiment data
      fetch(`https://dhpnet.pythonanywhere.com/api/sentiment?coin=${coin}&days=${days}`)
        .then(response => response.json())
        .then(data => {
          const labels = data.labels;
          const sentimentScores = data.sentimentScores;
          const positiveCounts = data.positiveCounts;
          const negativeCounts = data.negativeCounts;
          const neutralCounts = data.neutralCounts;
          const priceChanges = data.priceChanges;
          const topPositive = data.topPositive;
          const topNegative = data.topNegative;
  
          // Update Sentiment Line Chart
          sentimentLineChartInstance.data.labels = labels;
          sentimentLineChartInstance.data.datasets[0].data = sentimentScores;
          sentimentLineChartInstance.update();
  
          // Update Sentiment Bar Chart
          sentimentBarChartInstance.data.labels = labels;
          sentimentBarChartInstance.data.datasets[0].data = positiveCounts;
          sentimentBarChartInstance.data.datasets[1].data = negativeCounts;
          sentimentBarChartInstance.data.datasets[2].data = neutralCounts;
          sentimentBarChartInstance.update();
  
          // Update Sentiment Overlay Chart
          sentimentOverlayChartInstance.data.labels = labels;
          sentimentOverlayChartInstance.data.datasets[0].data = sentimentScores;
          sentimentOverlayChartInstance.data.datasets[1].data = priceChanges;
          sentimentOverlayChartInstance.update();
  
          // Update Top Positive and Negative Headlines
          document.getElementById('topPositive').innerHTML = topPositive.map(post => `<li>${post}</li>`).join('');
          document.getElementById('topNegative').innerHTML = topNegative.map(post => `<li>${post}</li>`).join('');
        })
        .catch(error => console.error('Error fetching sentiment data:', error));
  
      // Fetch word cloud data
      const limit = 100;
      fetch(`https://dhpnet.pythonanywhere.com/api/wordcloud?coin=${coin}&days=${days}&limit=${limit}`)
        .then(response => response.json())
        .then(data => {
          const words = data.words;
          if (words.length === 0 || words[0].text === 'no-keywords') {
            console.log("No keywords found.");
            return;
          }
  
          WordCloud(wordcloudDiv, {
            list: words.map(wordObj => [wordObj.text, wordObj.value]),
            gridSize: 15,
            weightFactor: 10,
            fontFamily: 'Poppins',
            color: 'random-dark',
            backgroundColor: '#2c5364'
          });
        })
        .catch(error => console.error('Error fetching word cloud data:', error));
  
      // Fetch correlation & directional accuracy
      fetch(`https://dhpnet.pythonanywhere.com/api/correlation?coin=${coin}&days=${days}`)
        .then(response => response.json())
        .then(data => {
          if (data.correlation === null || data.directional_accuracy === null) {
            correlationEl.textContent = "Correlation: N/A";
            dirAccuracyEl.textContent = "Directional Accuracy: N/A";
          } else {
            correlationEl.textContent = `Correlation: ${data.correlation}`;
            dirAccuracyEl.textContent = `Directional Accuracy: ${data.directional_accuracy}%`;
          }
        })
        .catch(error => console.error('Error fetching correlation data:', error));
    };

    
  
    fetchData();
    coinDropdown.addEventListener('change', fetchData);
    daysDropdown.addEventListener('change', fetchData);
  
    // Fullscreen feature for chart cards
    document.querySelectorAll('.fullscreen-btn').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        const targetId = btn.getAttribute('data-target');
        const chartCanvas = document.getElementById(targetId);
        if (!chartCanvas) return;
        const container = chartCanvas.parentElement;
        if (!document.fullscreenElement) {
          container.requestFullscreen?.() ||
            container.webkitRequestFullscreen?.() ||
            container.msRequestFullscreen?.();
        } else {
          document.exitFullscreen?.() ||
            document.webkitExitFullscreen?.() ||
            document.msExitFullscreen?.();
        }
      });
    });
  });
  