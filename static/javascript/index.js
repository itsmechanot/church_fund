// Global variables
let monthlyTrendChart;
let distributionChart;

// --- UTILITIES ---

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

function formatMoney(num) {
    if (isNaN(num)) return '0.00';
    return parseFloat(num).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getCurrentFundBalance(fundType) {
    const fundCard = document.querySelector(`.fund-card.${fundType} .fund-amount span`);
    if (fundCard) {
        return parseFloat(fundCard.textContent.replace(/[₱,]/g, '').trim()) || 0.00;
    }
    return 0.00;
}

function setFundBalance(fundType, newAmount) {
    const fundCard = document.querySelector(`.fund-card.${fundType} .fund-amount span`);
    if (fundCard) {
        fundCard.textContent = formatMoney(newAmount);
    }
}

// --- ADMIN BACK BUTTON LOGIC ---
function handleAdminBackButton(currentPageId) {
    const adminBackButton = document.getElementById('adminBackButton');
    const hamburgerMenu = document.getElementById('hamburgerMenu');
    
    if (adminBackButton && hamburgerMenu) {
        if (currentPageId === 'withdraw-page') {
            // Show admin back button, hide hamburger menu
            adminBackButton.style.display = 'flex';
            hamburgerMenu.style.display = 'none';
        } else {
            // Hide admin back button, show hamburger menu
            adminBackButton.style.display = 'none';
            hamburgerMenu.style.display = 'flex';
        }
    }
}

// --- NAVIGATION & PROFILE LOGIC (ADJUSTED) ---

const navLinks = document.querySelectorAll('.nav-menu a');
const pages = document.querySelectorAll('.page');
const defaultPageId = 'home'; // Set your intended default page ID

// Reusable function to activate a page based on its ID (now outside the loop)
function activatePage(targetId) {
    // 1. Deactivate all pages and clear animation
    pages.forEach(p => {
        p.classList.remove('active');
        const container = p.querySelector('.slide-up-container');
        if (container) container.style.animation = 'none';
    });

    // 2. Activate the target page
    const targetPage = document.getElementById(targetId);
    if (targetPage) {
        targetPage.classList.add('active');
        const container = targetPage.querySelector('.slide-up-container');
        if (container) {
            void container.offsetWidth; 
            container.style.animation = '';
        }
    }

    // 3. Update active nav link style
    navLinks.forEach(l => l.classList.remove('active'));
    // Find the link that points to the targetId
    const targetLink = document.querySelector(`.nav-menu a[href="#${targetId}"]`);
    if (targetLink) {
        targetLink.classList.add('active');
    }

    // 4. Handle specific page loads (like charts)
    if (targetId === 'funds-page') {
        setTimeout(initializeCharts, 100); 
    }
    
    // 5. Handle admin back button visibility
    handleAdminBackButton(targetId);
    
    // 6. Scroll to the top of the window
    window.scrollTo({ top: 0, behavior: 'smooth' });
}


// 1. Update Nav Links Listener to use pushState
navLinks.forEach(link => {
    link.addEventListener('click', e => {
        e.preventDefault();
        
        const targetHash = link.getAttribute('href'); // e.g., "#funds-page"
        const targetId = targetHash.substring(1); // e.g., "funds-page"
        
        // Update the URL hash in the browser history without reloading
        window.history.pushState(null, null, targetHash);
        
        activatePage(targetId);
    });
});

const profileIcon = document.getElementById('profileIcon');
const profileDropdown = document.getElementById('profileDropdown');

if (profileIcon && profileDropdown) {
    profileIcon.addEventListener('click', () => {
        profileDropdown.style.display = profileDropdown.style.display === 'block' ? 'none' : 'block';
    });
    window.addEventListener('click', (e) => {
        if (!profileIcon.contains(e.target) && !profileDropdown.contains(e.target)) {
            profileDropdown.style.display = 'none';
        }
    });
}

// --- FUNDS SECTION FUNCTIONALITY ---

// Essential element selections
const quickSplitBtn = document.getElementById('quick-split-btn');
const offeringsInput = document.getElementById('offerings-input');

// MODAL VARIABLES 
const splitOfferingsBtn = document.getElementById('split-offerings-btn'); 
const splitOfferingsModal = document.getElementById('splitOfferingsModal');
const percentageInputs = document.querySelectorAll('.percentage-input');
const saveSplitBtn = document.getElementById('saveSplitBtn'); 

const editFundsBtn = document.getElementById('edit-funds-btn');
const editFundsModal = document.getElementById('editFundsModal');
const editFundsForm = document.getElementById('editFundsForm');

const addFundBtn = document.getElementById('add-fund-btn');
const addFundModal = document.getElementById('addFundModal');
const addFundForm = document.getElementById('addFundForm');

const closeModals = document.querySelectorAll('.funds-close-modal');

// Modal Display/Closing Logic
if (editFundsBtn && editFundsModal) {
    editFundsBtn.addEventListener('click', () => {
        // Set values for specific fund modal... (Client side update logic omitted for brevity)
        editFundsModal.style.display = 'flex';
    });
}

if (addFundBtn && addFundModal) {
    addFundBtn.addEventListener('click', () => {
        addFundModal.style.display = 'flex';
    });
}

if (splitOfferingsBtn && splitOfferingsModal) {
    splitOfferingsBtn.addEventListener('click', () => {
        splitOfferingsModal.style.display = 'flex';
        if (typeof updateAndValidatePercentage === 'function') {
            updateAndValidatePercentage();
        }
    });
}

// Unified Modal Closing Logic
closeModals.forEach(btn => {
    btn.addEventListener('click', () => {
        if (editFundsModal) editFundsModal.style.display = 'none';
        if (addFundModal) addFundModal.style.display = 'none';
        if (splitOfferingsModal) splitOfferingsModal.style.display = 'none'; 
    });
});

// Add Fund Logic (AJAX Integrated)
if (addFundForm) {
    addFundForm.addEventListener('submit', function (e) {
        e.preventDefault();
        
        const fundName = document.getElementById('new-fund-name').value;
        const fundAmount = document.getElementById('new-fund-amount').value;
        const fundDesc = document.getElementById('new-fund-desc').value;

        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', csrftoken);
        formData.append('name', fundName); 
        formData.append('fund_type', fundName.toLowerCase().replace(/[^a-z0-9]+/g, ''));
        formData.append('current_balance', fundAmount);
        formData.append('description', fundDesc);
        
        fetch('/funds/create/', { 
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok || response.status === 302) {
                alert("Fund created successfully! Reloading page...");
                window.location.reload(); 
            } else {
                return response.json();
            }
        })
        .then(data => {
            if (data && data.errors) {
                 let errorMsg = "Fund creation failed with errors:\n";
                 for (const [field, messages] of Object.entries(data.errors)) {
                     errorMsg += `- ${field}: ${messages.join('; ')}\n`;
                 }
                 alert(errorMsg);
            }
        })
        .catch(error => {
            console.error('Fetch error during fund creation:', error);
            alert('An unexpected error occurred during fund creation.');
        });
    });
}

// **QUICK SPLIT ADJUSTMENT**
// 
// The previous AJAX logic for quick split has been REMOVED here.
// The form submission is now handled by the browser as a standard POST,
// which directs the user to the Django view, which correctly returns a redirect 
// after performing the single atomic transaction.
// The code block starting with 'if (quickSplitBtn && offeringsInput)' is GONE.
// 

// Withdrawal Logic (Expense Transaction)
const withdrawBtn = document.querySelector('.withdraw-btn');
const fundSelect = document.getElementById('fund-select'); 
const withdrawAmountInput = document.getElementById('withdraw-amount');
const withdrawReasonInput = document.getElementById('withdraw-reason');

if (withdrawBtn && fundSelect && withdrawAmountInput) {
    withdrawBtn.addEventListener('click', function () {
        const fundId = fundSelect.value;
        const amount = parseFloat(withdrawAmountInput.value);
        const description = withdrawReasonInput.value.trim();

        if (!fundId || isNaN(amount) || amount <= 0) {
            alert('Please select a fund and enter a valid amount.');
            return;
        }
        
        // DEBUG 8: Withdrawal data prepared
        console.log(`DEBUG 8: Preparing withdrawal for Fund ${fundId}. Amount: ${amount}`);

        // Use URLSearchParams for consistency with Quick Split fix
        const data = new URLSearchParams();
        data.append('fund', fundId);
        data.append('amount', amount);
        data.append('description', description || 'Withdrawal/Expense');
        data.append('transaction_type', 'Expense'); 

        fetch('/funds/transaction/', { 
            method: 'POST',
            headers: { 
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: data.toString()
        })
        .then(response => response.json().then(data => ({ status: response.status, body: data })))
        .then(({ status, body }) => {
            // DEBUG 9: Withdrawal response received
            console.log(`DEBUG 9: Withdrawal response status: ${status}. Body:`, body);
            
            if (status === 200 && body.success) {
                alert(`SUCCESS: ${body.message}`);
                
                const fundData = DYNAMIC_FUNDS_DATA.find(f => f.id == fundId); 
                if (fundData) {
                    setFundBalance(fundData.type, body.new_balance); 
                    updateFundStatistics();
                }
                
                withdrawAmountInput.value = '';
                withdrawReasonInput.value = '';
            } else {
                // DEBUG 10: Log withdrawal error
                console.error("DEBUG 10: Withdrawal failed:", body.errors);
                alert(`ERROR: ${body.message || 'Server error occurred.'}`);
            }
        })
        .catch(error => {
             console.error('DEBUG: Withdrawal fetch error:', error);
             alert('An unexpected network error occurred during withdrawal.');
        });
    });
}

// --- PERCENTAGE SPLIT SAVING & VALIDATION ---

// Calculates the total percentage assigned and updates the display
function updateAndValidatePercentage() {
    let total = 0;
    percentageInputs.forEach(input => {
        const value = parseFloat(input.value) || 0;
        total += value;
    });

    const totalDisplay = document.getElementById('totalPercentage');
    if (totalDisplay) {
        totalDisplay.textContent = `${total.toFixed(2)}%`;
        
        // 1. Clear both classes first
        totalDisplay.classList.remove('error', 'valid'); 
        
        // Use a small tolerance for floating point comparison
        if (total >= 99.99 && total <= 100.01) { 
            // 2. Add the success class (Green)
            totalDisplay.classList.add('valid'); 
            if (saveSplitBtn) saveSplitBtn.disabled = false;
        } else {
            // 3. Add the error class (Red)
            totalDisplay.classList.add('error');
            if (saveSplitBtn) saveSplitBtn.disabled = true;
        }
    }
}

if (percentageInputs) {
    percentageInputs.forEach(input => {
        input.addEventListener('input', updateAndValidatePercentage);
    });
}

// AJAX Submission for saving percentages to Django (save_default_split view)
if (saveSplitBtn) {
    saveSplitBtn.addEventListener('click', function (e) {
        e.preventDefault();
        
        updateAndValidatePercentage(); 
        if (saveSplitBtn.disabled) {
            alert("The total percentage must equal 100% before saving.");
            return;
        }

        // Using FormData is fine here as it's a simple form post to a Django view expecting it
        const formData = new FormData(document.getElementById('splitPercentageForm'));
        formData.append('csrfmiddlewaretoken', csrftoken);

        fetch('/funds/save_split/', { 
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                splitOfferingsModal.style.display = 'none';
                window.location.reload(); 
            } else {
                console.error('DEBUG: Error saving split:', data);
                alert(`Error saving split: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Fetch error during split save:', error);
            alert('An unexpected error occurred while saving the split configuration.');
        });
    });
}

// --- FUNDS STATISTICS AND CHARTS ---

function updateFundStatistics() {
    let total = 0;
    const fundCards = document.querySelectorAll('.funds-grid .fund-card');
    
    fundCards.forEach(card => {
        const amountElement = card.querySelector('.fund-amount span');
        if (amountElement) {
            const balance = parseFloat(amountElement.textContent.replace(/[₱,]/g, '').trim());
            if (!isNaN(balance)) {
                total += balance;
            }
        }
    });
    
    const totalFundsElem = document.querySelector('.funds-stat-value:first-child');
    if (totalFundsElem) {
        totalFundsElem.textContent = `₱${formatMoney(total)}`;
    }
    
    if (monthlyTrendChart && distributionChart) {
        updateCharts();
    }
}

function updateCharts() {
    const currentBalances = [];
    const fundCards = document.querySelectorAll('.funds-grid .fund-card');
    
    fundCards.forEach(card => {
        const amountElement = card.querySelector('.fund-amount span');
        if (amountElement) {
            currentBalances.push(parseFloat(amountElement.textContent.replace(/[₱,]/g, '').trim()));
        }
    });
    
    if (distributionChart) {
        distributionChart.data.datasets[0].data = currentBalances;
        distributionChart.update();
    }
    
    // (Monthly Trend Chart update logic omitted for brevity, assuming standard Chart.js functionality)
}


const fundTabs = document.querySelectorAll('.funds-tab');
if (fundTabs.length > 0) {
    fundTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            if (!monthlyTrendChart) return; 
            
            fundTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            const selectedFundLabel = tab.textContent.trim(); 
            filterChartData(selectedFundLabel);
        });
    });
}

function filterChartData(fundLabel) {
    if (!monthlyTrendChart) return;
    
    if (fundLabel === 'All Funds') {
        monthlyTrendChart.data.datasets.forEach(dataset => {
            dataset.hidden = false;
        });
    } else {
        monthlyTrendChart.data.datasets.forEach(dataset => {
            dataset.hidden = dataset.label !== fundLabel; 
        });
    }
    monthlyTrendChart.update();
}

// --- CHART INITIALIZATION ---

function initializeCharts() {
    if (typeof DYNAMIC_FUNDS_DATA === 'undefined' || DYNAMIC_FUNDS_DATA.length === 0) {
        console.warn("Dynamic fund data not found or empty. Charts cannot be initialized.");
        return;
    }

    const fundLabels = DYNAMIC_FUNDS_DATA.map(f => f.name);
    const fundBalances = DYNAMIC_FUNDS_DATA.map(f => f.balance);
    const colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796', '#f366b9'];
    
    // 1. Distribution Chart (Doughnut/Pie)
    const distributionCtx = document.getElementById('distributionChart');
    if (distributionCtx) {
        if (distributionChart) distributionChart.destroy(); 

        distributionChart = new Chart(distributionCtx, {
            type: 'doughnut',
            data: {
                labels: fundLabels, 
                datasets: [{
                    data: fundBalances, 
                    backgroundColor: colors,
                    hoverBackgroundColor: colors.map(c => c + 'AA'),
                }]
            },
            options: { maintainAspectRatio: false }
        });
    }

    // 2. Monthly Trend Chart (Line)
    const trendCtx = document.getElementById('monthlyTrendChart');
    if (trendCtx) {
        if (monthlyTrendChart) monthlyTrendChart.destroy();

        const dynamicDatasets = DYNAMIC_FUNDS_DATA.map((fund, index) => {
            const trendData = new Array(12).fill(0);
            trendData[new Date().getMonth()] = fund.balance; 

            return {
                label: fund.name,
                data: trendData,
                borderColor: colors[index % colors.length],
                backgroundColor: 'rgba(0,0,0,0)',
                tension: 0.4,
                hidden: index !== 0 
            };
        });

        monthlyTrendChart = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                datasets: dynamicDatasets
            },
            options: {
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', initializeCharts);


// WITHDRAW JS//
document.addEventListener('DOMContentLoaded', function() {
    const fundSelect = document.getElementById('fund-select');
    const balanceDisplay = document.getElementById('selected-fund-balance');
    
    // Function to format numbers for currency (PHP locale)
    function formatCurrency(amount) {
        // Use Intl.NumberFormat for proper localization and thousands separators
        return new Intl.NumberFormat('en-PH', {
            style: 'currency',
            currency: 'PHP',
            minimumFractionDigits: 2,
        }).format(amount);
    }

    // Set initial display to formatted zero
    if (balanceDisplay) {
        balanceDisplay.textContent = formatCurrency(0); 
    }

    if (fundSelect) {
        fundSelect.addEventListener('change', function() {
            // 1. Get the currently selected option element
            const selectedOption = fundSelect.options[fundSelect.selectedIndex];
            
            // 2. Read the raw balance from the data-balance attribute
            let rawBalance = selectedOption.getAttribute('data-balance');
            
            // If no fund is selected or balance is missing, reset display
            if (!rawBalance) {
                if (balanceDisplay) balanceDisplay.textContent = formatCurrency(0);
                return;
            }

            // 3. Convert to a float and update the display text
            const balanceValue = parseFloat(rawBalance);
            if (balanceDisplay) balanceDisplay.textContent = formatCurrency(balanceValue);
        });
    }
});


// --- HAMBURGER MENU FUNCTIONALITY ---
document.addEventListener('DOMContentLoaded', function() {
    const hamburgerMenu = document.getElementById('hamburgerMenu');
    const navRight = document.getElementById('navRight');
    const body = document.body;
    
    // Create overlay element
    const overlay = document.createElement('div');
    overlay.className = 'nav-overlay';
    overlay.id = 'navOverlay';
    body.appendChild(overlay);
    
    // Toggle mobile menu
    function toggleMobileMenu() {
        hamburgerMenu.classList.toggle('active');
        navRight.classList.toggle('active');
        overlay.classList.toggle('active');
        body.classList.toggle('nav-open');
    }
    
    // Close mobile menu
    function closeMobileMenu() {
        hamburgerMenu.classList.remove('active');
        navRight.classList.remove('active');
        overlay.classList.remove('active');
        body.classList.remove('nav-open');
    }
    
    // Hamburger menu click
    if (hamburgerMenu) {
        hamburgerMenu.addEventListener('click', toggleMobileMenu);
    }
    
    // Overlay click to close
    overlay.addEventListener('click', closeMobileMenu);
    
    // Close menu when navigation link is clicked
    const navLinks = document.querySelectorAll('.nav-menu a, .mobile-profile-links a');
    navLinks.forEach(link => {
        link.addEventListener('click', closeMobileMenu);
    });
    
    // Close menu on window resize if screen becomes larger
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            closeMobileMenu();
        }
    });
});

// --- HASH-BASED NAVIGATION INITIALIZATION (FIX) ---
// This handles direct link access (e.g., /#funds-page) and browser history (back/forward)
document.addEventListener('DOMContentLoaded', function() {
    
    // Get the ID from the URL hash (e.g., 'funds-page' from '#funds-page')
    const currentHashId = window.location.hash.substring(1); 
    
    let pageToActivate = defaultPageId; // Use the defaultPageId defined globally

    // Check if a valid page ID is in the URL hash
    if (currentHashId && document.getElementById(currentHashId)) {
        pageToActivate = currentHashId;
    } 

    // Activate the determined page on load
    activatePage(pageToActivate);
    
    // Handle admin back button on initial load
    handleAdminBackButton(pageToActivate); 
    
    // Handle browser back/forward buttons (popstate event)
    window.addEventListener('popstate', function() {
        const hashOnPop = window.location.hash.substring(1);
        // If hash is empty, return to the default page
        activatePage(hashOnPop || defaultPageId);
    });
});