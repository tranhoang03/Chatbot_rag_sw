// Biến toàn cục
const chatHistory = document.getElementById('chat-history');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const imageUpload = document.getElementById('image-upload');
const uploadButton = document.getElementById('upload-button');
const micButton = document.getElementById('mic-button');
const suggestedQuestionsArea = document.querySelector('.suggested-questions-area');
const leftShadow = document.querySelector('.scroll-shadow-left');
const rightShadow = document.querySelector('.scroll-shadow-right');
const voiceSettingsButton = document.getElementById('voice-settings-button');
const voiceDropdownContent = document.getElementById('voice-dropdown-content');
const voiceOptions = document.querySelectorAll('.voice-option');

// Biến để lưu trữ đối tượng nhận dạng giọng nói
let recognition = null;
// Biến để kiểm tra xem trình duyệt có hỗ trợ Web Speech API không
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
// Biến để lưu trữ trạng thái đang ghi âm
let isRecording = false;
// Biến để lưu trữ trạng thái đang phát âm thanh
let isPlaying = false;
// Biến để lưu trữ đối tượng âm thanh
let audioContext = null;
let audioSource = null;
// Giọng đọc mặc định
let currentVoice = "huyen";
// Biến để theo dõi xem người dùng đang sử dụng chế độ nhập giọng nói hay không
let voiceInputMode = false;

// Category mapping for quick lookup
const categoryMap = {
    'Classic Espresso Drinks': 'classic_espresso',
    'Coffee': 'coffee',
    'Frappuccino Blended Coffee': 'frappuccino_coffee',
    'Frappuccino Blended Crème': 'frappuccino_creme',
    'Shaken Iced Beverages': 'iced_beverages',
    'Signature Espresso Drinks': 'signature_espresso',
    'Smoothies': 'smoothies',
    'Tazo Tea Drinks': 'tea'
};

// Variables for drag scrolling
let isDown = false;
let startX;
let scrollLeft;

// Functions
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('chat-message');
    messageDiv.classList.add(role === 'user' ? 'user-message' : 'assistant-message');

    content = content.replace(/\(?(https?:\/\/[^\s]+)\)?/g, '<a href="$1" target="_blank" style="color: inherit;">$1</a>');
    content = content.replace(/\n/g, '<br>');

    const contentWrapper = document.createElement('div');
    contentWrapper.classList.add('message-content');
    contentWrapper.innerHTML = content;

    messageDiv.appendChild(contentWrapper);
    chatHistory.appendChild(messageDiv);

    chatHistory.scrollTop = chatHistory.scrollHeight;
    ensureSuggestedQuestionsVisible();

    return messageDiv;
}

function ensureSuggestedQuestionsVisible() {
    if (typeof updateScrollShadows === 'function') {
        setTimeout(updateScrollShadows, 100);
    }
}

function addImageMessage(role, imageDataUrl) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('chat-message');
    messageDiv.classList.add(role === 'user' ? 'user-message' : 'assistant-message');
    messageDiv.classList.add('image-message');

    const imgContainer = document.createElement('div');
    imgContainer.style.width = '240px';
    imgContainer.style.height = '240px';
    imgContainer.style.overflow = 'hidden';

    const img = document.createElement('img');
    img.src = imageDataUrl;
    img.alt = "Uploaded Image";

    imgContainer.appendChild(img);
    messageDiv.appendChild(imgContainer);
    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    ensureSuggestedQuestionsVisible();
}

function displayProductImages(productImages) {
    if (!productImages || Object.keys(productImages).length === 0) {
        return;
    }

    const productsDiv = document.createElement('div');
    productsDiv.classList.add('chat-message', 'assistant-message', 'product-message');

    const titleRow = document.createElement('div');
    titleRow.classList.add('title-row');

    const titleElem = document.createElement('strong');
    titleElem.textContent = 'Sản phẩm được đề cập:';
    titleElem.classList.add('product-title');

    titleRow.appendChild(titleElem);
    productsDiv.appendChild(titleRow);

    const gridContainer = document.createElement('div');
    gridContainer.classList.add('product-grid');

    const productCount = Object.keys(productImages).length;
    if (productCount === 1) {
        gridContainer.classList.add('grid-1-item');
    } else if (productCount === 2) {
        gridContainer.classList.add('grid-2-items');
    }

    for (const product of productImages) {
        const productCard = document.createElement('div');
        productCard.style.textAlign = 'center';

        const imageContainer = document.createElement('div');
        imageContainer.classList.add('product-image-container');

        const img = document.createElement('img');
        img.src = product.image;
        img.alt = product.name;
        img.classList.add('product-image');

        const nameElem = document.createElement('div');
        nameElem.textContent = product.name;
        nameElem.classList.add('product-name');
        nameElem.style.color = '#181825';

        imageContainer.appendChild(img);
        productCard.appendChild(imageContainer);
        productCard.appendChild(nameElem);
        gridContainer.appendChild(productCard);
    }

    productsDiv.appendChild(gridContainer);
    chatHistory.appendChild(productsDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    ensureSuggestedQuestionsVisible();
}

async function sendMessage() {
    const prompt = userInput.value.trim();
    if (!prompt) return;

    const currentVoiceMode = voiceInputMode;
    console.log("Trạng thái voiceInputMode khi gửi tin nhắn:", currentVoiceMode);

    addMessage('user', prompt);
    userInput.value = '';
    sendButton.disabled = true;
    userInput.disabled = true;
    sendButton.textContent = '...';

    const thinkingDiv = document.createElement('div');
    thinkingDiv.classList.add('chat-message', 'assistant-message');
    thinkingDiv.innerHTML = '<i>Đang xử lý...🤔</i>';
    thinkingDiv.id = 'thinking-indicator';
    chatHistory.appendChild(thinkingDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    try {
        const response = await fetch("/chat", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt: prompt })
        });

        const indicator = document.getElementById('thinking-indicator');
        if (indicator) {
            chatHistory.removeChild(indicator);
        }

        if (!response.ok) {
            let errorMsg = `Lỗi ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Ignore if body isn't JSON */ }
            addMessage('assistant', `⚠️ Xin lỗi, đã có lỗi xảy ra: ${errorMsg}`);
        } else {
            const data = await response.json();
            if (data.role === 'assistant') {
                const messageDiv = addMessage('assistant', data.content);

                if (data.content && currentVoiceMode) {
                    console.log("Đang phát âm thanh cho phản hồi (chế độ giọng nói)");
                    textToSpeech(data.content);
                } else if (data.content) {
                    console.log("Không phát âm thanh vì không ở chế độ nhập giọng nói");
                }

                voiceInputMode = false;

                if (data.product_images) {
                    displayProductImages(data.product_images);
                }
            }
        }

    } catch (error) {
        console.error('Error sending message:', error);
        const indicator = document.getElementById('thinking-indicator');
        if (indicator) {
            chatHistory.removeChild(indicator);
        }
        addMessage('assistant', '⚠️ Xin lỗi, đã có lỗi kết nối mạng. Vui lòng thử lại.');
    } finally {
        sendButton.disabled = false;
        userInput.disabled = false;
        sendButton.textContent = 'Gửi';
        userInput.focus();
    }
}

async function processImageBackend(formData) {
    try {
        const currentVoiceMode = voiceInputMode;
        console.log("Trạng thái voiceInputMode khi xử lý hình ảnh:", currentVoiceMode);

        const response = await fetch("/process_image", {
            method: 'POST',
            body: formData,
        });

        const indicator = document.getElementById('image-processing-indicator');
        if (indicator) {
            chatHistory.removeChild(indicator);
        }

        if (!response.ok) {
            throw new Error(`Lỗi ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        const messageDiv = addMessage('assistant', result.content);

        if (result.content && currentVoiceMode) {
            console.log("Đang phát âm thanh cho hình ảnh (chế độ giọng nói)");
            textToSpeech(result.content);
        } else if (result.content) {
            console.log("Không phát âm thanh cho hình ảnh vì không ở chế độ nhập giọng nói");
        }

        voiceInputMode = false;

        if (result.product_images) {
            displayProductImages(result.product_images);
        }
    } catch (error) {
        const indicator = document.getElementById('image-processing-indicator');
        if (indicator) {
            chatHistory.removeChild(indicator);
        }
        console.error('Error processing image:', error);
        addMessage('assistant', '⚠️ Xin lỗi, đã có lỗi xảy ra khi xử lý hình ảnh.');
    }
}

function initSpeechRecognition() {
    if (!SpeechRecognition) {
        console.error("Trình duyệt của bạn không hỗ trợ Web Speech API");
        micButton.style.display = "none";
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'vi-VN';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = function() {
        isRecording = true;
        micButton.classList.add('recording');
        console.log("Bắt đầu ghi âm...");
    };

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        userInput.value = transcript;
        console.log("Đã nhận dạng: " + transcript);
    };

    recognition.onerror = function(event) {
        console.error("Lỗi nhận dạng giọng nói: " + event.error);
        stopRecording();
    };

    recognition.onend = function() {
        stopRecording();
        if (userInput.value.trim() !== '') {
            console.log("Đã nhận dạng giọng nói, gửi tin nhắn");
            sendMessage();
        }
    };
}

function startRecording() {
    if (!recognition) {
        initSpeechRecognition();
    }

    if (recognition) {
        try {
            voiceInputMode = true;
            console.log("Đã bật chế độ nhập giọng nói, voiceInputMode =", voiceInputMode);
            recognition.start();
        } catch (e) {
            console.error("Lỗi khi bắt đầu ghi âm: ", e);
        }
    }
}

function stopRecording() {
    if (recognition) {
        try {
            recognition.stop();
        } catch (e) {
            console.error("Lỗi khi dừng ghi âm: ", e);
        }
    }
    isRecording = false;
    micButton.classList.remove('recording');
}

async function textToSpeech(text) {
    try {
        console.log(`Đang chuyển đổi văn bản thành giọng nói với giọng ${currentVoice}...`);
        console.log(`Nội dung: "${text.substring(0, 100)}${text.length > 100 ? '...' : ''}"`);

        const response = await fetch("/text-to-speech", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                voice: currentVoice
            })
        });

        if (!response.ok) {
            throw new Error(`Lỗi ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        if (!data.audio) {
            throw new Error("Không nhận được dữ liệu âm thanh từ server");
        }

        console.log("Đã nhận dữ liệu âm thanh, đang chuẩn bị phát...");

        const audio = new Audio(`data:audio/mp3;base64,${data.audio}`);

        isPlaying = true;
        audio.play();

        audio.onended = function() {
            isPlaying = false;
            console.log("Phát âm thanh hoàn tất");
        };

        audio.onerror = function(e) {
            isPlaying = false;
            console.error("Lỗi khi phát âm thanh:", e);
        };

    } catch (error) {
        console.error('Lỗi khi chuyển đổi văn bản thành giọng nói:', error);
    }
}

function changeVoice(voice) {
    currentVoice = voice;
    console.log(`Đã chuyển sang giọng đọc: ${voice}`);
}

function updateScrollShadows() {
    if (suggestedQuestionsArea.scrollLeft > 10) {
        leftShadow.style.opacity = '1';
    } else {
        leftShadow.style.opacity = '0';
    }

    if (suggestedQuestionsArea.scrollWidth - suggestedQuestionsArea.scrollLeft - suggestedQuestionsArea.clientWidth < 10) {
        rightShadow.style.opacity = '0';
    } else {
        rightShadow.style.opacity = '1';
    }
}

function updateActiveVoice() {
    voiceOptions.forEach(option => {
        const voiceValue = option.getAttribute('onclick').match(/'([^']+)'/)[1];
        if (voiceValue === currentVoice) {
            option.classList.add('active');
        } else {
            option.classList.remove('active');
        }
    });
}

async function processSuggestedQuery(queryId, questionText) {
    addMessage('user', `Cho tôi xem ${questionText}`);

    const thinkingDiv = document.createElement('div');
    thinkingDiv.classList.add('chat-message', 'assistant-message');
    thinkingDiv.innerHTML = '<i>Đang tải dữ liệu menu...🤔</i>';
    thinkingDiv.id = 'suggested-query-indicator';
    chatHistory.appendChild(thinkingDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    try {
        const response = await fetch("/suggested_query", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query_id: queryId })
        });

        removeLoadingIndicator();

        if (!response.ok) {
            throw new Error(`Lỗi ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.role === 'assistant' && data.content_type === 'menu_data') {
            displayMenuData(data);
        }
    } catch (error) {
        console.error('Error processing suggested query:', error);
        removeLoadingIndicator();
        addMessage('assistant', `⚠️ Lỗi khi xử lý truy vấn: ${error.message}`);
    }
}

function removeLoadingIndicator() {
    const indicator = document.getElementById('suggested-query-indicator');
    if (indicator) {
        chatHistory.removeChild(indicator);
    }
}

function displayMenuData(data) {
    let messageContent = `<span class="menu-title">${data.data.title}</span>`;

    if (data.data.type === 'categories') {
        displayCategoriesData(data, messageContent);
    } else if (data.data.type === 'products') {
        displayProductsData(data, messageContent);
    }
}

function displayCategoriesData(data, messageContent) {
    messageContent += '<span class="menu-subtitle">Các danh mục đồ uống:</span>';

    data.data.items.forEach(category => {
        messageContent += `<div class="menu-item" data-category="${category.name}">- ${category.name}</div>\n`;
    });

    const messageDiv = addMessage('assistant', messageContent);

    setTimeout(addCategoryClickHandlers, 100);
}

function addCategoryClickHandlers() {
    const categoryItems = document.querySelectorAll('.menu-item');
    categoryItems.forEach(item => {
        item.style.cursor = 'pointer';
        item.addEventListener('click', () => {
            const categoryName = item.dataset.category;
            const queryId = categoryMap[categoryName];
            if (queryId) {
                const button = document.querySelector(`.suggested-question[data-query-id="${queryId}"]`);
                if (button) {
                    button.click();
                }
            }
        });
    });
}

function displayProductsData(data, messageContent) {
    messageContent += `<span class="menu-subtitle">Các sản phẩm trong danh mục ${data.data.title}:</span>`;

    data.data.items.forEach(product => {
        messageContent += `<div class="menu-product"><span class="product-name">- ${product.name}</span><span class="product-description">${product.description}</span></div>\n`;
    });

    addMessage('assistant', messageContent);

    if (data.product_images && data.product_images.length > 0) {
        displayProductImages(data.product_images);
    }
}

// Event Listeners
sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', function(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');

sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('sidebar-collapsed');
    sidebarToggle.textContent = sidebar.classList.contains('sidebar-collapsed') ? '☰' : '✕';
});

userInput.focus();

uploadButton.addEventListener('click', () => {
    imageUpload.click();
});

imageUpload.addEventListener('change', async () => {
    const file = imageUpload.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = async function(e) {
            const imageDataUrl = e.target.result;
            addImageMessage('user', imageDataUrl);

            const processingMsgDiv = addMessage('assistant', '<i>Đang xử lý ảnh...</i>');
            processingMsgDiv.id = 'image-processing-indicator';

            const formData = new FormData();
            formData.append('image', file);
            await processImageBackend(formData);
        }
        reader.readAsDataURL(file);
    }

    imageUpload.value = null;
});

window.addEventListener('beforeunload', function() {
    fetch('/reset_session');
});

micButton.addEventListener('click', function() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
});

voiceSettingsButton.addEventListener('click', function() {
    voiceDropdownContent.classList.toggle('show');
});

window.addEventListener('click', function(event) {
    if (!event.target.matches('#voice-settings-button') &&
        !event.target.closest('#voice-settings-button') &&
        !event.target.matches('.voice-dropdown-content') &&
        !event.target.closest('.voice-dropdown-content')) {
        if (voiceDropdownContent.classList.contains('show')) {
            voiceDropdownContent.classList.remove('show');
        }
    }
});

// Override changeVoice function to update UI
const originalChangeVoice = changeVoice;
changeVoice = function(voice) {
    originalChangeVoice(voice);
    updateActiveVoice();
    voiceDropdownContent.classList.remove('show');
};

// Initialize
initSpeechRecognition();
updateActiveVoice();
updateScrollShadows();

// Update on scroll
suggestedQuestionsArea.addEventListener('scroll', updateScrollShadows);

// Update on window resize
window.addEventListener('resize', updateScrollShadows);

// Mouse events for drag scrolling
suggestedQuestionsArea.addEventListener('mousedown', (e) => {
    isDown = true;
    suggestedQuestionsArea.classList.add('dragging');
    suggestedQuestionsArea.style.cursor = 'grabbing';
    startX = e.pageX - suggestedQuestionsArea.offsetLeft;
    scrollLeft = suggestedQuestionsArea.scrollLeft;
    e.preventDefault();
});

suggestedQuestionsArea.addEventListener('mouseleave', () => {
    isDown = false;
    suggestedQuestionsArea.classList.remove('dragging');
    suggestedQuestionsArea.style.cursor = 'grab';
});

suggestedQuestionsArea.addEventListener('mouseup', () => {
    isDown = false;
    suggestedQuestionsArea.classList.remove('dragging');
    suggestedQuestionsArea.style.cursor = 'grab';
});

suggestedQuestionsArea.addEventListener('mousemove', (e) => {
    if (!isDown) return;
    e.preventDefault();
    const x = e.pageX - suggestedQuestionsArea.offsetLeft;
    const walk = (x - startX) * 2;
    suggestedQuestionsArea.scrollLeft = scrollLeft - walk;
});

// Touch events for mobile drag scrolling
suggestedQuestionsArea.addEventListener('touchstart', (e) => {
    isDown = true;
    suggestedQuestionsArea.classList.add('dragging');
    startX = e.touches[0].pageX - suggestedQuestionsArea.offsetLeft;
    scrollLeft = suggestedQuestionsArea.scrollLeft;
}, { passive: true });

suggestedQuestionsArea.addEventListener('touchend', () => {
    isDown = false;
    suggestedQuestionsArea.classList.remove('dragging');
});

suggestedQuestionsArea.addEventListener('touchmove', (e) => {
    if (!isDown) return;
    const x = e.touches[0].pageX - suggestedQuestionsArea.offsetLeft;
    const walk = (x - startX) * 2;
    suggestedQuestionsArea.scrollLeft = scrollLeft - walk;
}, { passive: true });

// Handle suggested questions
const suggestedQuestions = document.querySelectorAll('.suggested-question');
suggestedQuestions.forEach(question => {
    question.addEventListener('click', function() {
        const queryId = this.dataset.queryId;
        const questionText = this.innerText.trim();
        processSuggestedQuery(queryId, questionText);
    });
});