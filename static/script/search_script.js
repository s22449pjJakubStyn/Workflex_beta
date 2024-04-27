// Funkcja obsługująca zdarzenie wprowadzania tekstu w polu wyszukiwania
function handleSearchInput() {
    const query = document.getElementById('global_search_query').value;

    // Sprawdź, czy zapytanie jest puste
    if (!query.trim()) {
        // Jeśli zapytanie jest puste, wyczyść wyniki na stronie
        const resultsDiv = document.getElementById('searchResults');
        resultsDiv.innerHTML = '';
        return;
    }

    // Wykonaj asynchroniczne zapytanie do endpointu /searcher
    fetch(`/searcher?query=${query}`)
        .then(response => response.json())
        .then(data => {
            // Zaktualizuj wyniki na bieżącej stronie
            const resultsDiv = document.getElementById('searchResults');
            resultsDiv.innerHTML = ''; // Wyczyść wyniki przed aktualizacją

            if (data.employees.length > 0) {
                data.employees.forEach(employee => {
                    const employeeDiv = document.createElement('div');
                    // Dodaj link do strony employee_searched.html z parametrem employee_id
                    employeeDiv.innerHTML = `<a href="/employee_searched/${employee.employee_id}">${employee.name} ${employee.surname} (${employee.email})</a>`;
                    resultsDiv.appendChild(employeeDiv);
                });
            } else {
                // Jeżeli brak wyników, wyświetl komunikat
                const noResultsDiv = document.createElement('div');
                noResultsDiv.textContent = 'Brak wyników.';
                resultsDiv.appendChild(noResultsDiv);
            }
        })
        .catch(error => {
            console.error('Error during search:', error);
        });
}

// Dodaj nasłuchiwanie na zdarzenie wprowadzania tekstu
document.getElementById('global_search_query').addEventListener('input', handleSearchInput);