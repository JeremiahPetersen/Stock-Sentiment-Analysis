import yfinance as yf
import pandas as pd
import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import MinMaxScaler
from xgboost import XGBClassifier
from datetime import datetime

# Technical indicators
def sma(data, window):
    return data['Close'].rolling(window=window).mean()

def rsi(data, window):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def bollinger_bands(data, window):
    sma = data['Close'].rolling(window=window).mean()
    std_dev = data['Close'].rolling(window=window).std()
    upper_band = sma + (2 * std_dev)
    lower_band = sma - (2 * std_dev)
    return upper_band, lower_band

def macd(data):
    exp12 = data['Close'].ewm(span=12, adjust=False).mean()
    exp26 = data['Close'].ewm(span=26, adjust=False).mean()
    macd = exp12 - exp26
    signal_line = macd.ewm(span=9, adjust=False).mean()
    return macd, signal_line

# Preprocess data
def preprocess_data(stock_ticker, start_date, end_date):
    data = yf.download(stock_ticker, start=start_date, end=end_date)
    data['Returns'] = data['Close'].pct_change()
    data['Direction'] = np.where(data['Returns'] > 0, 1, -1)
    data['SMA'] = sma(data, window=14)
    data['RSI'] = rsi(data, window=14)
    data['BB_Upper'], data['BB_Lower'] = bollinger_bands(data, window=14)
    data['MACD'], data['Signal_Line'] = macd(data)
    data = data.dropna()
    return data

# Prepare features
def prepare_features(data, sentiment_analyzer):
    data['Sentiment'] = data['Headline'].apply(lambda x: sentiment_analyzer.polarity_scores(x)['compound'])
    features = data[['Sentiment', 'SMA', 'RSI', 'BB_Upper', 'BB_Lower', 'MACD', 'Signal_Line']]
    return features

# Train and evaluate model
def train_and_evaluate_model(model, model_params, X_train, y_train, X_test, y_test):
    grid_search = GridSearchCV(model, model_params, cv=10)
    grid_search.fit(X_train, y_train)
    best_model = grid_search.best_estimator_
    y_pred = best_model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    return accuracy, y_pred, best_model

def main(stock_ticker, news_headline):
    sentiment_analyzer = SentimentIntensityAnalyzer()
    
    # Historical Data
    start_date = '1993-02-01'
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Preprocess data
    stock_data = preprocess_data(stock_ticker, start_date, end_date)
    
    # Load sample news data (replace with real news data)
    news_data = pd.DataFrame({'Date': stock_data.index, 'Headline': ['Sample headline'] * len(stock_data)})
    
    # Merge stock_data and news_data
    merged_data = stock_data.merge(news_data, on='Date', how='inner').dropna()
    
    # Prepare features
    X = prepare_features(merged_data, sentiment_analyzer)
    
    # Normalize the features
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    X = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)

    y = merged_data['Direction']
    
    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train and evaluate different models
models = {
    "Logistic Regression": (LogisticRegression(), {"C": [0.001, 0.01, 0.1, 1, 10, 100]}),
    "Random Forest": (RandomForestClassifier(random_state=42), {"n_estimators": [50, 100, 150], "max_depth": [5, 10, 15], "min_samples_leaf": [2, 4]}),
    "Support Vector Machine": (SVC(random_state=42), {"C": [0.1, 1, 10], "kernel": ['linear', 'rbf']}),
    "XGBoost": (XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss'), {"n_estimators": [50, 100, 150], "max_depth": [3, 5, 7]}),
    "K-Nearest Neighbors": (KNeighborsClassifier(), {"n_neighbors": [3, 5, 7, 9]}),
    "Decision Tree": (DecisionTreeClassifier(random_state=42), {"max_depth": [5, 10, 15], "min_samples_leaf": [2, 4, 6]}),
    "AdaBoost": (AdaBoostClassifier(random_state=42), {"n_estimators": [50, 100, 150], "learning_rate": [0.1, 0.5, 1.0]}),
    "Neural Network (MLP)": (MLPClassifier(random_state=42, max_iter=1000), {"hidden_layer_sizes": [(50,), (100,)], "alpha": [0.0001, 0.001, 0.01]})
}

for model_name, (model, model_params) in models.items():
    accuracy, y_pred, best_model = train_and_evaluate_model(model, model_params, X_train, y_train, X_test, y_test)
    print(f"{model_name} - Best Model: {best_model}")
    print(f"{model_name} - Accuracy Score: {accuracy}")
    print(f"{model_name} - Classification Report: \n{classification_report(y_test, y_pred)}")

    # Predict next day movement
    sentiment = sentiment_analyzer.polarity_scores(news_headline)['compound']
    scaled_input = scaler.transform([[sentiment, X_test['SMA'].iloc[-1], X_test['RSI'].iloc[-1], X_test['BB_Upper'].iloc[-1], X_test['BB_Lower'].iloc[-1], X_test['MACD'].iloc[-1], X_test['Signal_Line'].iloc[-1]]])
    prediction = best_model.predict(scaled_input)
    movement = "up" if prediction[0] > 0 else "down"

    print(f"Based on the news headline '{news_headline}', the predicted movement for {stock_ticker} using {model_name} is {movement}.")
    print()

if __name__ == "__main__":
    stock_ticker = input("Enter the stock ticker: ")
    news_headline = input("Enter the news headline: ")
    main(stock_ticker, news_headline)
