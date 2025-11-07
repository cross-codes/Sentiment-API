document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('search-form');
    const usernameInput = document.getElementById('username-input');
    const tweetsList = document.getElementById('tweets-list');
    const loader = document.getElementById('loader');
    const messageArea = document.getElementById('message-area');

    const API_URL = 'http://127.0.0.1:8000';
    const SENTIMENT_API_URL = `${API_URL}/classification/`;

    searchForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const username = usernameInput.value.trim();
        if (!username) return;

        clearResults();
        loader.classList.remove('hidden');
        try {
            const response = await fetch(`${API_URL}/api/tweets/${username}`);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch tweets.');
            }
            const tweets = await response.json();
            displayTweets(tweets);

        } catch (error) {
            messageArea.textContent = `Error: ${error.message}`;
        } finally {
            loader.classList.add('hidden');
        }
    });

    function displayTweets(tweets) {
        if (!tweets || tweets.length === 0) {
            messageArea.textContent = 'No tweets found for this user.';
            return;
        }

        tweets.forEach(tweet => {
            const listItem = document.createElement('li');
            listItem.className = 'tweet-item';
            listItem.innerHTML = `
                <p class="tweet-text">${tweet.text}</p>
                <div class="tweet-actions">
                    <button class="analyze-btn" data-tweet-text="${encodeURIComponent(tweet.text)}">Analyze Sentiment</button>
                    <div class="sentiment-result-container"></div>
                </div>
            `;
            tweetsList.appendChild(listItem);
        });
    }

    tweetsList.addEventListener('click', async (event) => {
        if (event.target.classList.contains('analyze-btn')) {
            const button = event.target;
            const tweetText = decodeURIComponent(button.getAttribute('data-tweet-text'));
            const resultContainer = button.nextElementSibling;

            button.disabled = true;
            button.textContent = 'Analyzing...';
            try {
                const sentimentResponse = await fetch(SENTIMENT_API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: tweetText })
                });

                if (!sentimentResponse.ok) throw new Error('Sentiment API request failed.');
                const sentimentData = await sentimentResponse.json();
                const sentiment = sentimentData.predicted_class.toLowerCase();

                resultContainer.innerHTML = `<span class="sentiment-result ${sentiment}">${sentiment.charAt(0).toUpperCase() + sentiment.slice(1)}</span>`;
                button.classList.add('hidden');

            } catch (error) {
                resultContainer.innerHTML = `<span class="sentiment-result negative">Error</span>`;
                button.textContent = 'Analyze Sentiment';
                button.disabled = false;
            }
        }
    });

    function clearResults() {
        tweetsList.innerHTML = '';
        messageArea.textContent = '';
    }
});
