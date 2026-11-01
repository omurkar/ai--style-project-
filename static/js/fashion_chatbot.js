/**
 * AI Fashion Advisor Chatbot Client
 * Handles natural language input, mandatory profiling interceptor,
 * and clickable interactive product card rendering.
 */

(function () {
    let chatProfile = {
        age_group: null,
        gender_identity: null,
        clothing_category: null
    };
    let messageHistory = [];
    let isWaitingResponse = false;

    // DOM Elements
    let launcherBtn, chatWindow, closeBtn, resetBtn, messagesBox, inputField, sendBtn, typingIndicator, profileBar;

    function initChatbot() {
        launcherBtn = document.getElementById("styleChatLauncher");
        chatWindow = document.getElementById("styleChatWindow");
        closeBtn = document.getElementById("styleChatClose");
        resetBtn = document.getElementById("styleChatReset");
        messagesBox = document.getElementById("styleChatMessages");
        inputField = document.getElementById("styleChatInput");
        sendBtn = document.getElementById("styleChatSend");
        typingIndicator = document.getElementById("styleChatTyping");
        profileBar = document.getElementById("styleChatProfileBar");

        if (!launcherBtn || !chatWindow) return;

        launcherBtn.addEventListener("click", toggleChatWindow);
        if (closeBtn) closeBtn.addEventListener("click", toggleChatWindow);
        if (resetBtn) resetBtn.addEventListener("click", resetConversation);

        if (sendBtn) {
            sendBtn.addEventListener("click", handleSendMessage);
        }

        if (inputField) {
            inputField.addEventListener("keydown", function (e) {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                }
            });
        }

        // Fetch existing session profile
        fetchProfile();
    }

    function toggleChatWindow() {
        const isOpen = chatWindow.classList.contains("open");
        if (isOpen) {
            chatWindow.classList.remove("open");
        } else {
            chatWindow.classList.add("open");
            if (inputField) inputField.focus();

            // First time opened and empty -> trigger greeting
            if (messagesBox && messagesBox.children.length <= 1) {
                triggerInitialPrompt();
            }
        }
    }

    async function fetchProfile() {
        try {
            const res = await fetch("/api/chat/profile");
            if (res.ok) {
                const data = await res.json();
                if (data.profile) {
                    chatProfile = Object.assign(chatProfile, data.profile);
                    updateProfileBadgeBar();
                }
            }
        } catch (e) {
            console.warn("[Chatbot] Could not fetch profile", e);
        }
    }

    function updateProfileBadgeBar() {
        if (!profileBar) return;
        const chips = [];
        if (chatProfile.age_group) {
            chips.push(`<span class="profile-chip">Age: ${chatProfile.age_group}</span>`);
        }
        if (chatProfile.gender_identity) {
            chips.push(`<span class="profile-chip">Gender: ${chatProfile.gender_identity}</span>`);
        }
        if (chatProfile.clothing_category) {
            chips.push(`<span class="profile-chip">Dept: ${chatProfile.clothing_category}</span>`);
        }

        if (chips.length > 0) {
            profileBar.innerHTML = `<span style="font-weight:700;">Profile:</span> ` + chips.join(" ");
            profileBar.style.display = "flex";
        } else {
            profileBar.style.display = "none";
        }
    }

    async function triggerInitialPrompt() {
        showTyping(true);
        try {
            const res = await fetch("/api/chat/message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: "Hi",
                    profile: chatProfile,
                    history: []
                })
            });
            const data = await res.json();
            showTyping(false);
            if (data.profile) chatProfile = data.profile;
            updateProfileBadgeBar();
            appendBotMessage(data.reply, data.quick_replies, data.products);
        } catch (err) {
            showTyping(false);
            appendBotMessage("Welcome to AI Style Advisor! ✨ What kind of outfit or look are you shopping for today?", [
                "Festive Diwali Outfit",
                "Job Interview Look",
                "Casual Weekend Wear"
            ]);
        }
    }

    async function resetConversation() {
        if (isWaitingResponse) return;
        messagesBox.innerHTML = "";
        chatProfile = { age_group: null, gender_identity: null, clothing_category: null };
        messageHistory = [];
        updateProfileBadgeBar();
        showTyping(true);
        try {
            const res = await fetch("/api/chat/reset", { method: "POST" });
            const data = await res.json();
            showTyping(false);
            appendBotMessage(data.reply, data.quick_replies);
        } catch (err) {
            showTyping(false);
            triggerInitialPrompt();
        }
    }

    function handleSendMessage() {
        if (isWaitingResponse || !inputField) return;
        const text = inputField.value.trim();
        if (!text) return;

        inputField.value = "";
        appendUserMessage(text);
        sendQueryToBackend(text);
    }

    window.sendChatQuickReply = function (text) {
        if (isWaitingResponse) return;
        appendUserMessage(text);
        sendQueryToBackend(text);
    };

    async function sendQueryToBackend(userText) {
        isWaitingResponse = true;
        if (sendBtn) sendBtn.disabled = true;
        showTyping(true);

        messageHistory.push({ role: "user", text: userText });

        try {
            const response = await fetch("/api/chat/message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: userText,
                    profile: chatProfile,
                    history: messageHistory.slice(-6)
                })
            });

            const data = await response.json();
            showTyping(false);
            isWaitingResponse = false;
            if (sendBtn) sendBtn.disabled = false;

            if (data.profile) {
                chatProfile = Object.assign(chatProfile, data.profile);
                updateProfileBadgeBar();
            }

            appendBotMessage(data.reply, data.quick_replies, data.products);
            messageHistory.push({ role: "bot", text: data.reply });
        } catch (error) {
            console.error("[Chatbot Error]", error);
            showTyping(false);
            isWaitingResponse = false;
            if (sendBtn) sendBtn.disabled = false;
            appendBotMessage("I encountered a momentary connection error. Let's try again! What style are you looking for?");
        }
    }

    function appendUserMessage(text) {
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble user";
        bubble.textContent = text;
        messagesBox.appendChild(bubble);
        scrollToBottom();
    }

    function appendBotMessage(text, quickReplies = [], products = []) {
        const container = document.createElement("div");
        container.style.display = "flex";
        container.style.flexDirection = "column";
        container.style.alignSelf = "flex-start";
        container.style.maxWidth = "96%";

        // Text bubble
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble bot";
        // Parse simple bold markdown
        const formatted = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        bubble.innerHTML = formatted;
        container.appendChild(bubble);

        // Clickable Product Cards (Task 5)
        if (products && products.length > 0) {
            const prodCarousel = document.createElement("div");
            prodCarousel.className = "chat-products-container";

            products.forEach(prod => {
                const card = document.createElement("div");
                card.className = "chat-product-card";
                card.setAttribute("title", `Click to view ${prod.outfit_name}`);

                // Click event redirects user to product detail page
                card.onclick = function (e) {
                    // If clicked button specifically, let button handler proceed
                    if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON') return;
                    window.location.href = prod.detail_url;
                };

                card.innerHTML = `
                    <div class="product-card-img-wrap">
                        <img class="product-card-img" src="${prod.image_url}" alt="${prod.outfit_name}" onerror="this.src='https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=400&q=80';">
                        <span class="product-card-badge">${prod.occasion || prod.category}</span>
                    </div>
                    <div class="product-card-body">
                        <div class="product-card-title">${prod.outfit_name}</div>
                        <div class="product-card-price-row">
                            <span class="product-card-price">₹${prod.price}</span>
                            <span class="product-card-meta">${prod.colour}</span>
                        </div>
                        <div class="product-card-actions">
                            <a href="${prod.detail_url}" class="btn-card-action primary">View Details →</a>
                            <a href="${prod.tryon_url}" class="btn-card-action tryon">Try On 🪄</a>
                        </div>
                    </div>
                `;
                prodCarousel.appendChild(card);
            });

            container.appendChild(prodCarousel);
        }

        // Quick replies chips
        if (quickReplies && quickReplies.length > 0) {
            const qrRow = document.createElement("div");
            qrRow.className = "chat-quick-replies";
            quickReplies.forEach(qr => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "quick-reply-btn";
                btn.textContent = qr;
                btn.onclick = function () {
                    window.sendChatQuickReply(qr);
                };
                qrRow.appendChild(btn);
            });
            container.appendChild(qrRow);
        }

        messagesBox.appendChild(container);
        scrollToBottom();
    }

    function showTyping(show) {
        if (!typingIndicator) return;
        typingIndicator.style.display = show ? "flex" : "none";
        if (show) scrollToBottom();
    }

    function scrollToBottom() {
        if (!messagesBox) return;
        setTimeout(() => {
            messagesBox.scrollTop = messagesBox.scrollHeight;
        }, 30);
    }

    // Initialize when DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initChatbot);
    } else {
        initChatbot();
    }
})();

