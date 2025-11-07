import nltk, emoji, string
from nltk import pos_tag
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

nltk.download("punkt")
nltk.download("wordnet")
nltk.download("averaged_perceptron_tagger")
nltk.download("stopwords")


class TextPreProcessor:
    def __init__(self, custom_stopwords=None):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words("english"))
        if custom_stopwords:
            self.stop_words.update(custom_stopwords)

    def _get_wordnet_pos(self, word):
        tag = pos_tag([word])[0][1][0].upper()
        tag_dict = {
            "J": wordnet.ADJ,
            "N": wordnet.NOUN,
            "V": wordnet.VERB,
            "R": wordnet.ADV,
        }
        return tag_dict.get(tag, wordnet.NOUN)

    def preprocess(self, text):
        if not isinstance(text, str):
            return ""

        text = text.lower()
        text = emoji.demojize(text)
        text = text.translate(str.maketrans("", "", string.punctuation))
        tokens = word_tokenize(text)
        filtered_tokens = []
        for token in tokens:
            if token not in self.stop_words and token.isalpha():
                pos = self._get_wordnet_pos(token)
                lemma = self.lemmatizer.lemmatize(token, pos)
                filtered_tokens.append(lemma)

        return " ".join(filtered_tokens)
