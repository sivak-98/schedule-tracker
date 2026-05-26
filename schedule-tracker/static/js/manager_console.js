









                        document.addEventListener('DOMContentLoaded', function() {
                            // Initialize Flatpickr for range selection (not for start/end dates)
                            flatpickr(".datepicker-range", {
                                mode: "multiple",  // Enable multiple date selection
                                dateFormat: "Y-m-d",  // Format for backend compatibility
                            });
    
                            // Initialize Materialize select for team filter
                            M.FormSelect.init(document.querySelectorAll('select'));
                        });
                    

          document.addEventListener('DOMContentLoaded', function () {
            const teamCalendarTab = document.getElementById('team-calendar-tab');
            const calendarEl = document.getElementById('team-calendar-view');
            const downloadButton = document.getElementById('download-report');
  
            // Initialize Materialize Select
            M.FormSelect.init(document.querySelectorAll('select'));
  
            teamCalendarTab.addEventListener('shown.bs.tab', function () {
              if (!calendarEl.innerHTML) {
                var eventsData = {{ calendar_events|tojson }}; // Ensure this is passed correctly from Flask
  
                // Functions to extract unique teams and users
                function getUniqueTeams(events) {
                  return [...new Set(events.map(event => event.team))];
                }
  
                function getUniqueUsers(events) {
                  return [...new Set(events.map(event => event.user))];
                }
  
                var uniqueTeams = getUniqueTeams(eventsData);
                var uniqueUsers = getUniqueUsers(eventsData);
  
                // Populate Team Filter
                var teamCalendarFilter = document.getElementById('team-calendar-filter');
                uniqueTeams.forEach(function (team) {
                  var option = document.createElement('option');
                  option.value = team;
                  option.textContent = team;
                  teamCalendarFilter.appendChild(option);
                });
                M.FormSelect.init(teamCalendarFilter); // Re-initialize Materialize select
  
                // Populate User Filter
                var userCalendarFilter = document.getElementById('user-calendar-filter');
                uniqueUsers.forEach(function (user) {
                  var option = document.createElement('option');
                  option.value = user;
                  option.textContent = user;
                  userCalendarFilter.appendChild(option);
                });
                M.FormSelect.init(userCalendarFilter); // Re-initialize Materialize select
  
                // Initialize FullCalendar
                var calendar = new FullCalendar.Calendar(calendarEl, {
                  initialView: 'dayGridMonth',
                  themeSystem: 'bootstrap',
                  headerToolbar: {
                    start: 'title',
                    center: '',
                    end: 'today prev,next',
                  },
                  events: eventsData,
                  eventClassNames: 'z-depth-1 rounded', // Add Material style to events
                  eventClick: function (info) {
                    M.toast({ html: `Event: ${info.event.title}<br>Date: ${info.event.start.toLocaleDateString()}<br>Description: ${info.event.extendedProps.description || 'No description available'}` });
                  },
                });
  
                // Render the calendar
                calendar.render();
  
                // Filter events on Team/User selection
                function filterEvents() {
                  var selectedTeam = teamCalendarFilter.value;
                  var selectedUser = userCalendarFilter.value;
  
                  var filteredEvents = eventsData.filter(function (event) {
                    return (!selectedTeam || event.team === selectedTeam) &&
                          (!selectedUser || event.user === selectedUser);
                  });
  
                  calendar.removeAllEvents();
                  calendar.addEventSource(filteredEvents);
                }
  
                teamCalendarFilter.addEventListener('change', filterEvents);
                userCalendarFilter.addEventListener('change', filterEvents);
  
                // Download Report Functionality for Current Month
                downloadButton.addEventListener('click', function () {
                  var calendarDate = calendar.getDate(); // Get the currently displayed date
                  var startOfMonth = new Date(calendarDate.getFullYear(), calendarDate.getMonth(), 1);
                  var endOfMonth = new Date(calendarDate.getFullYear(), calendarDate.getMonth() + 1, 0);
  
                  // Get events within the current month
                  var filteredEvents = calendar.getEvents().filter(function (event) {
                    return event.start >= startOfMonth && event.start <= endOfMonth;
                  }).map(function (event) {
                    return {
                      Date: event.start.toLocaleDateString(),
                      Team: event.extendedProps.team || 'N/A',
                      User: event.extendedProps.user || 'N/A',
                      Shift: event.title.includes(':') ? event.title.split(':')[1].trim() : event.title, // Extract text after colon
                    };
                  });
  
                  if (filteredEvents.length === 0) {
                    M.toast({ html: 'No events available for the selected month.' });
                    return;
                  }
  
                  // Generate and download the Excel file
                  var worksheet = XLSX.utils.json_to_sheet(filteredEvents);
                  var workbook = XLSX.utils.book_new();
                  XLSX.utils.book_append_sheet(workbook, worksheet, 'Events Report');
                  XLSX.writeFile(workbook, 'Team_Calendar_Report_Current_Month.xlsx');
                });
              }
            });
          });
        


          document.addEventListener('DOMContentLoaded', function() {
              M.AutoInit();
          });
      

document.addEventListener('DOMContentLoaded', function() {
  var elems = document.querySelectorAll('.tabs');
  M.Tabs.init(elems);
});


document.addEventListener('DOMContentLoaded', function() {
  // Initialize Materialize select elements
  var selectElems = document.querySelectorAll('select');
  M.FormSelect.init(selectElems);

  // Team filter logic
  var teamFilter = document.getElementById('team-filter');
  if (teamFilter) {
    teamFilter.addEventListener('change', function() {
      var selectedTeam = this.value.replace(/\s+/g, '-'); // Normalize selected team
      var rows = document.querySelectorAll('.user-row');

      rows.forEach(function(row) {
        if (selectedTeam === 'all' || row.classList.contains(selectedTeam)) {
          row.style.display = ''; // Show matching rows
        } else {
          row.style.display = 'none'; // Hide non-matching rows
        }
      });
    });
  }
});

