import joblib
from sklearn.ensemble import RandomForestRegressor


class AlphaTrainer:

    def __init__(self):
        self.model = RandomForestRegressor(
            n_estimators=200,
            max_depth=6,
            n_jobs=-1,
            random_state=42
        )

    def fit(self, X, y):
        self.model.fit(X, y)

    def predict(self, X):
        return self.model.predict(X)

    def save(self, path):
        joblib.dump(self.model, path)

    def load(self, path):
        self.model = joblib.load(path)