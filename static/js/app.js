/* ==========================================================================
   INDIA GOVERNMENT WELFARE PORTAL — DYNAMIC FRONTEND OVERHAUL
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // Initialise Lucide Icons
    lucide.createIcons();

    // 1. STATE & GLOBAL CACHES
    let currentStep = 1;
    const totalSteps = 6;
    let lastMatches = [];
    let allSchemesList = []; // Used in admin search

    // 2. DOM ELEMENTS
    const prevBtn = document.getElementById("wizard-prev-btn");
    const nextBtn = document.getElementById("wizard-next-btn");
    const progressFill = document.getElementById("wizard-progress-fill");
    const stepLabel = document.getElementById("wizard-step-label");
    
    const tabWizardBtn = document.getElementById("tab-wizard");
    const tabChatBtn = document.getElementById("tab-chat");
    const contentWizard = document.getElementById("content-wizard");
    const contentChat = document.getElementById("content-chat");
    
    const chatInput = document.getElementById("chat-input-field");
    const chatSendBtn = document.getElementById("chat-send-btn");
    const chatMessages = document.getElementById("chat-messages");
    const syncTagsContainer = document.getElementById("sync-tags-container");

    const schemesList = document.getElementById("schemes-list");
    const resultsCount = document.getElementById("results-count");
    
    // Modals
    const detailsModal = document.getElementById("details-modal");
    const modalCloseBtn = document.getElementById("modal-close-btn");
    
    const adminToggleBtn = document.getElementById("admin-toggle-btn");
    const adminModal = document.getElementById("admin-modal");
    const adminCloseBtn = document.getElementById("admin-close-btn");
    const adminTabList = document.getElementById("btn-admin-list");
    const adminTabAdd = document.getElementById("btn-admin-add");
    const adminTabListContent = document.getElementById("admin-tab-list-content");
    const adminTabAddContent = document.getElementById("admin-tab-add-content");
    const adminSearchInput = document.getElementById("admin-search-input");
    const adminSchemesTable = document.getElementById("admin-schemes-table");

    // 3. TAB & SIDEBAR NAVIGATION
    tabWizardBtn.addEventListener("click", () => switchTab("wizard"));
    tabChatBtn.addEventListener("click", () => switchTab("chat"));

    function switchTab(tab) {
        if (tab === "wizard") {
            tabWizardBtn.classList.add("active");
            tabChatBtn.classList.remove("active");
            contentWizard.classList.add("active");
            contentChat.classList.remove("active");
        } else {
            tabWizardBtn.classList.remove("active");
            tabChatBtn.classList.add("active");
            contentWizard.classList.remove("active");
            contentChat.classList.add("active");
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    // 4. WIZARD STEP NAVIGATION
    prevBtn.addEventListener("click", () => navigateStep(-1));
    nextBtn.addEventListener("click", () => navigateStep(1));

    function navigateStep(direction) {
        const activeStep = document.querySelector(`.wizard-step[data-step="${currentStep}"]`);
        activeStep.classList.remove("active");

        currentStep += direction;
        
        const newStep = document.querySelector(`.wizard-step[data-step="${currentStep}"]`);
        newStep.classList.add("active");

        // Update progress bar
        const percent = Math.round((currentStep / totalSteps) * 100);
        progressFill.style.width = `${percent}%`;
        stepLabel.innerText = `Step ${currentStep} of ${totalSteps}`;

        // Disable buttons accordingly
        prevBtn.disabled = currentStep === 1;
        if (currentStep === totalSteps) {
            nextBtn.querySelector("span").innerText = "View Results";
            nextBtn.querySelector("i").setAttribute("data-lucide", "check-circle");
        } else {
            nextBtn.querySelector("span").innerText = "Next Step";
            nextBtn.querySelector("i").setAttribute("data-lucide", "chevron-right");
        }
        lucide.createIcons();
    }

    // 5. SLIDER CONTROLS & DIGNIFIED INCOME LABELS
    const incomeSlider = document.getElementById("income-slider");
    const incomeAmountText = document.getElementById("income-amount-text");
    const incomeLevelBadge = document.getElementById("income-level-badge");

    incomeSlider.addEventListener("input", (e) => {
        updateIncomeUI(parseInt(e.target.value));
        matchProfile();
    });

    window.setIncome = function(val) {
        incomeSlider.value = val;
        updateIncomeUI(val);
        matchProfile();
    };

    function updateIncomeUI(value) {
        incomeAmountText.innerText = `₹ ${value.toLocaleString("en-IN")}`;
        
        if (value <= 100000) {
            incomeLevelBadge.innerText = "Priority Support (Antyodaya / PHH)";
            incomeLevelBadge.style.background = "rgba(16, 185, 129, 0.08)";
            incomeLevelBadge.style.color = "#10b981";
            incomeLevelBadge.style.borderColor = "rgba(16, 185, 129, 0.2)";
        } else if (value <= 300000) {
            incomeLevelBadge.innerText = "Welfare Support Eligible";
            incomeLevelBadge.style.background = "rgba(99, 102, 241, 0.08)";
            incomeLevelBadge.style.color = "#6366f1";
            incomeLevelBadge.style.borderColor = "rgba(99, 102, 241, 0.2)";
        } else if (value <= 600000) {
            incomeLevelBadge.innerText = "General Welfare Eligible";
            incomeLevelBadge.style.background = "rgba(20, 184, 166, 0.08)";
            incomeLevelBadge.style.color = "#14b8a6";
            incomeLevelBadge.style.borderColor = "rgba(20, 184, 166, 0.2)";
        } else {
            incomeLevelBadge.innerText = "General Category";
            incomeLevelBadge.style.background = "rgba(100, 116, 139, 0.08)";
            incomeLevelBadge.style.color = "#64748b";
            incomeLevelBadge.style.borderColor = "rgba(100, 116, 139, 0.2)";
        }
    }

    // 6. REAL-TIME MATCHING EVENT LISTENERS
    const profileForm = document.getElementById("profile-form");
    profileForm.addEventListener("change", (e) => {
        if (e.target.name) {
            matchProfile();
        }
    });

    // 7. GET FORM STATE & MATCH SCHEMES
    function getFormState() {
        const formData = new FormData(profileForm);
        return {
            state: formData.get("state"),
            occupation: formData.get("occupation"),
            income: parseInt(incomeSlider.value),
            family: formData.get("family"),
            special: formData.get("special"),
            gender: formData.get("gender")
        };
    }

    // SKELETON LOADER ANIMATIONS
    function showSkeletonLoaders() {
        schemesList.innerHTML = `
            <div class="skeleton-card skeleton-shimmer">
                <div class="skeleton-block sk-badge"></div>
                <div class="skeleton-block sk-title" style="margin-top: 10px;"></div>
                <div class="skeleton-block sk-dept" style="margin-top: 5px;"></div>
                <div class="skeleton-block sk-benefit" style="margin-top: 15px;"></div>
                <div class="skeleton-block sk-reason" style="margin-top: 10px;"></div>
                <div class="skeleton-block sk-btn" style="margin-top: 10px;"></div>
            </div>
            <div class="skeleton-card skeleton-shimmer">
                <div class="skeleton-block sk-badge"></div>
                <div class="skeleton-block sk-title" style="margin-top: 10px;"></div>
                <div class="skeleton-block sk-dept" style="margin-top: 5px;"></div>
                <div class="skeleton-block sk-benefit" style="margin-top: 15px;"></div>
                <div class="skeleton-block sk-reason" style="margin-top: 10px;"></div>
                <div class="skeleton-block sk-btn" style="margin-top: 10px;"></div>
            </div>
        `;
    }

    function matchProfile() {
        const state = getFormState();
        showSkeletonLoaders();
        
        fetch("/api/match", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(state)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                lastMatches = data.matches;
                // Add a small 200ms delay to make the premium shimmer look visible and smooth!
                setTimeout(() => {
                    renderSchemes(data.matches);
                }, 200);
            }
        })
        .catch(err => {
            console.error("Error matching profile:", err);
            schemesList.innerHTML = `<p style="color:#ef4444; text-align:center;">Communication error loading results.</p>`;
        });
    }

    // 8. RENDER SCHEME CARDS
    function renderSchemes(matches) {
        resultsCount.innerText = `${matches.length} Matches`;
        
        if (matches.length === 0) {
            schemesList.innerHTML = `
                <div class="blank-state">
                    <div class="blank-state-glowing-circle">
                        <i data-lucide="search"></i>
                    </div>
                    <h3>No Matching Schemes Found</h3>
                    <p>No schemes matched this profile criteria. Try updating your selections or adjusting your annual household income bounds.</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        schemesList.innerHTML = "";
        matches.forEach((s, idx) => {
            const card = document.createElement("div");
            card.className = "scheme-card";
            
            const levelClass = s.level === "central" ? "badge-indigo" : "badge-saffron";
            const levelLabel = s.level.toUpperCase() + " PROGRAM";
            
            const reasonsHtml = s.match_reasons.map(reason => `
                <span class="reason-item">
                    <i data-lucide="check"></i>
                    <span>Qualifies for ${reason}</span>
                </span>
            `).join("");

            card.innerHTML = `
                <div class="scheme-card-header">
                    <div>
                        <span class="badge ${levelClass}">${levelLabel}</span>
                        <p class="mt-1">${s.ministry || "Ministry Department"}</p>
                        <h3 class="mt-1">${s.name}</h3>
                    </div>
                </div>
                <div class="scheme-benefit-badge mt-1">
                    <span class="scheme-benefit-label">Financial Benefit:</span>
                    <p class="scheme-benefit-value">${s.benefit_amount}</p>
                </div>
                <div class="scheme-qualify-reasons mt-1">
                    ${reasonsHtml}
                </div>
                <button class="btn btn-secondary mt-1 view-details-btn" data-index="${idx}">
                    <span>View Application Details</span>
                    <i data-lucide="chevron-right"></i>
                </button>
            `;
            schemesList.appendChild(card);
        });

        // Add event listeners to buttons
        document.querySelectorAll(".view-details-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const index = parseInt(btn.getAttribute("data-index"));
                showSchemeDetails(matches[index]);
            });
        });

        lucide.createIcons();
    }

    // 9. SCHEME DETAILS MODAL
    function showSchemeDetails(scheme) {
        document.getElementById("modal-level").className = `badge ${scheme.level === "central" ? "badge-indigo" : "badge-saffron"}`;
        document.getElementById("modal-level").innerText = scheme.level.toUpperCase() + " PROGRAM";
        document.getElementById("modal-name").innerText = scheme.name;
        document.getElementById("modal-ministry").innerText = scheme.ministry || "Ministry Department";
        document.getElementById("modal-benefit").innerText = scheme.benefit_amount;
        document.getElementById("modal-description").innerText = scheme.benefit_description || "Welfare support aid program.";
        document.getElementById("modal-eligibility").innerText = scheme.eligibility_note || "Matches your profile filters.";
        
        // Documents Needed checklist
        const docsList = document.getElementById("modal-documents");
        docsList.innerHTML = "";
        
        const docs = scheme.documents_needed ? scheme.documents_needed.split(",") : ["Aadhaar card", "Income Certificate"];
        docs.forEach(doc => {
            const li = document.createElement("li");
            li.innerHTML = `<i data-lucide="check"></i> <span>${doc.trim()}</span>`;
            docsList.appendChild(li);
        });

        // Application Procedure
        document.getElementById("modal-apply").innerText = scheme.how_to_apply || "Visit your block development office or Nadakacheri centre.";
        
        // Portal URL
        const link = document.getElementById("modal-link");
        if (scheme.url) {
            link.href = scheme.url;
            link.style.display = "inline-flex";
        } else {
            link.style.display = "none";
        }

        detailsModal.classList.add("active");
        lucide.createIcons();
    }

    modalCloseBtn.addEventListener("click", () => {
        detailsModal.classList.remove("active");
    });
    
    detailsModal.addEventListener("click", (e) => {
        if (e.target === detailsModal) {
            detailsModal.classList.remove("active");
        }
    });

    // 10. AI CHATBOT SYSTEM
    chatSendBtn.addEventListener("click", handleUserMessage);
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            handleUserMessage();
        }
    });

    window.sendSuggestion = function(text) {
        chatInput.value = text;
        handleUserMessage();
    };

    function handleUserMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Render User Message
        appendMessage("user", text, "👤");
        chatInput.value = "";

        // Render typing indicator
        const typingId = appendTypingIndicator();
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Call backend API
        fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                last_matches: lastMatches
            })
        })
        .then(res => res.json())
        .then(data => {
            removeTypingIndicator(typingId);
            
            if (data.success) {
                // Render Bot message
                appendMessage("bot", data.reply, "🙏");
                
                // If it is not a detail request, sync profile and matches!
                if (!data.is_detail && data.profile) {
                    syncFormFromAI(data.profile);
                    if (data.matches) {
                        lastMatches = data.matches;
                        renderSchemes(data.matches);
                    }
                }
            } else {
                appendMessage("bot", `⚠️ Error: ${data.error || "Could not generate response"}`, "🤖");
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(err => {
            removeTypingIndicator(typingId);
            appendMessage("bot", "⚠️ Server communication error. Please check your network connection.", "🤖");
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    function appendMessage(sender, text, avatar) {
        const msg = document.createElement("div");
        msg.className = `chat-msg ${sender}`;
        
        // Convert Markdown-like text to HTML
        let formattedText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');

        msg.innerHTML = `
            <div class="msg-avatar-wrapper">${avatar}</div>
            <div class="msg-card">
                <p>${formattedText}</p>
            </div>
        `;
        chatMessages.appendChild(msg);
    }

    function appendTypingIndicator() {
        const id = "typing-" + Date.now();
        const msg = document.createElement("div");
        msg.className = "chat-msg bot";
        msg.id = id;
        msg.innerHTML = `
            <div class="msg-avatar-wrapper">⏳</div>
            <div class="msg-card">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(msg);
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    // 11. AI FORM SYNC & DIGNIFIED BADGES
    function syncFormFromAI(profile) {
        syncTagsContainer.innerHTML = "";
        let syncCount = 0;

        // Mapping raw keys to dignified label overrides
        const tagLabels = {
            "state": "State",
            "occupation": "Livelihood",
            "family": "Family Status",
            "special": "Demographic",
            "gender": "Gender",
            "income": "Welfare Tier"
        };

        const occupationLabels = {
            "farmer": "Smallholder Farmer",
            "daily_wage": "Daily Wage Labour",
            "self_employed": "Self-Employed",
            "unemployed": "Not Employed",
            "salaried": "Salaried Employee",
            "other": "Other Livelihood"
        };

        const familyLabels = {
            "single": "Single",
            "married": "Married",
            "widow": "Widowed",
            "single_parent": "Single Parent"
        };

        const specialLabels = {
            "disabled": "Special Needs",
            "senior": "Senior Citizen",
            "pregnant": "Pregnant / Lactating",
            "student": "Student",
            "none": "General Category"
        };

        // Loop keys and apply selections
        const keys = ["state", "occupation", "family", "special", "gender"];
        keys.forEach(key => {
            const val = profile[key];
            if (val) {
                const radio = profileForm.querySelector(`input[name="${key}"][value="${val}"]`);
                if (radio) {
                    radio.checked = true;
                    syncCount++;
                    
                    // Retrieve dignified val representation
                    let dignifiedVal = val;
                    if (key === "occupation") dignifiedVal = occupationLabels[val] || val;
                    if (key === "family") dignifiedVal = familyLabels[val] || val;
                    if (key === "special") dignifiedVal = specialLabels[val] || val;
                    if (key === "gender") dignifiedVal = val.charAt(0).toUpperCase() + val.slice(1);
                    
                    addSyncBadge(tagLabels[key], dignifiedVal);
                }
            }
        });

        // Handle Income slider
        if (profile.income !== undefined && profile.income !== null) {
            incomeSlider.value = profile.income;
            updateIncomeUI(profile.income);
            syncCount++;
            
            let welfareTier = "General Group";
            if (profile.income <= 100000) welfareTier = "Antyodaya / PHH";
            else if (profile.income <= 300000) welfareTier = "Welfare Support";
            
            addSyncBadge(tagLabels["income"], welfareTier);
        }

        if (syncCount === 0) {
            syncTagsContainer.innerHTML = `<span class="empty-sync">No details active</span>`;
        }
    }

    function addSyncBadge(label, val) {
        const badge = document.createElement("span");
        badge.className = "sync-badge";
        badge.innerText = `${label}: ${val}`;
        syncTagsContainer.appendChild(badge);
    }

    // 12. ADMIN PORTAL LOGIC
    adminToggleBtn.addEventListener("click", () => {
        loadAdminSchemes();
        adminModal.classList.add("active");
    });
    
    adminCloseBtn.addEventListener("click", () => {
        adminModal.classList.remove("active");
    });
    
    adminModal.addEventListener("click", (e) => {
        if (e.target === adminModal) {
            adminModal.classList.remove("active");
        }
    });

    adminTabList.addEventListener("click", () => {
        adminTabList.classList.add("active");
        adminTabAdd.classList.remove("active");
        adminTabListContent.classList.add("active");
        adminTabAddContent.classList.remove("active");
    });

    adminTabAdd.addEventListener("click", () => {
        adminTabAdd.classList.add("active");
        adminTabList.classList.remove("active");
        adminTabAddContent.classList.add("active");
        adminTabListContent.classList.remove("active");
    });

    // Fetch and list existing schemes in admin
    function loadAdminSchemes() {
        adminSchemesTable.innerHTML = `<p style="text-align:center; padding:1.5rem; color:var(--text-muted);">Loading schemes from database...</p>`;
        
        fetch("/api/schemes")
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                allSchemesList = data.schemes;
                renderAdminSchemes(data.schemes);
            }
        })
        .catch(err => {
            adminSchemesTable.innerHTML = `<p style="color:#ef4444; text-align:center; padding:1.5rem;">Error loading database.</p>`;
        });
    }

    function renderAdminSchemes(schemes) {
        if (schemes.length === 0) {
            adminSchemesTable.innerHTML = `<p style="text-align:center; padding:1.5rem; color:var(--text-muted);">No schemes inside database.</p>`;
            return;
        }

        adminSchemesTable.innerHTML = "";
        schemes.forEach(s => {
            const row = document.createElement("div");
            row.className = "admin-row";
            row.innerHTML = `
                <div class="admin-row-info">
                    <h5>${s.name}</h5>
                    <p>${s.ministry || "No Department"} • ${s.level.toUpperCase()} • ${s.benefit_amount}</p>
                </div>
                <button class="btn btn-danger admin-delete-btn" data-id="${s.id}">
                    <i data-lucide="trash-2"></i>
                    <span>Delete</span>
                </button>
            `;
            adminSchemesTable.appendChild(row);
        });

        // Delete Event
        document.querySelectorAll(".admin-delete-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const id = btn.getAttribute("data-id");
                if (confirm("Are you sure you want to delete this scheme permanently from schemes.db?")) {
                    deleteSchemeFromDB(id);
                }
            });
        });

        lucide.createIcons();
    }

    // Search Admin Schemes
    adminSearchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        const filtered = allSchemesList.filter(s => 
            s.name.toLowerCase().includes(query) || 
            (s.ministry && s.ministry.toLowerCase().includes(query))
        );
        renderAdminSchemes(filtered);
    });

    function deleteSchemeFromDB(id) {
        fetch(`/api/schemes/${id}`, {
            method: "DELETE"
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert("Scheme deleted successfully!");
                loadAdminSchemes();
                matchProfile(); // Update active matching results
            } else {
                alert("Error: " + data.error);
            }
        })
        .catch(err => alert("Communication error: " + err));
    }

    // Submit new scheme to Database
    window.submitNewScheme = function() {
        const schemeData = {
            name: document.getElementById("form-name").value,
            level: document.getElementById("form-level").value,
            ministry: document.getElementById("form-ministry").value,
            benefit_amount: document.getElementById("form-benefit-amt").value,
            benefit_description: document.getElementById("form-desc").value,
            how_to_apply: document.getElementById("form-apply").value,
            documents_needed: document.getElementById("form-docs").value,
            states: document.getElementById("form-states").value,
            min_income: document.getElementById("form-min-income").value,
            max_income: document.getElementById("form-max-income").value,
            
            // Occupations
            for_farmer: document.getElementById("chk-occ-farmer").checked ? 1 : 0,
            for_daily_wage: document.getElementById("chk-occ-daily-wage").checked ? 1 : 0,
            for_unemployed: document.getElementById("chk-occ-unemployed").checked ? 1 : 0,
            for_self_employed: document.getElementById("chk-occ-self-employed").checked ? 1 : 0,
            for_salaried: document.getElementById("chk-occ-salaried").checked ? 1 : 0,
            for_any_occupation: document.getElementById("chk-occ-any").checked ? 1 : 0,

            // Family
            for_widow: document.getElementById("chk-fam-widow").checked ? 1 : 0,
            for_single_parent: document.getElementById("chk-fam-single-parent").checked ? 1 : 0,
            for_married: document.getElementById("chk-fam-married").checked ? 1 : 0,
            for_single: document.getElementById("chk-fam-single").checked ? 1 : 0,
            for_any_family: document.getElementById("chk-fam-any").checked ? 1 : 0,

            // Special
            for_disabled: document.getElementById("chk-sp-disabled").checked ? 1 : 0,
            for_senior: document.getElementById("chk-sp-senior").checked ? 1 : 0,
            for_pregnant: document.getElementById("chk-sp-pregnant").checked ? 1 : 0,
            for_student: document.getElementById("chk-sp-student").checked ? 1 : 0,
            for_any_special: document.getElementById("chk-sp-any").checked ? 1 : 0,

            // Gender & details
            for_women: parseInt(document.getElementById("form-women-only").value),
            url: document.getElementById("form-url").value,
            eligibility_note: document.getElementById("form-eligibility-note").value
        };

        fetch("/api/schemes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(schemeData)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert("Welfare scheme successfully saved to schemes.db!");
                document.getElementById("add-scheme-form").reset();
                
                // Switch back to list tab
                adminTabList.click();
                loadAdminSchemes();
                matchProfile(); // Update active matching results
            } else {
                alert("Error: " + data.error);
            }
        })
        .catch(err => alert("Communication error: " + err));
    };

    // Run first initialization match
    matchProfile();
});
