import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Mettre à jour l'état pour afficher l'UI de fallback
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Logger l'erreur pour le débogage
    console.error('❌ ErrorBoundary a capturé une erreur:', error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  render() {
    if (this.state.hasError) {
      // UI de fallback personnalisée
      return (
        <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
          <div className="text-center bg-white p-6 rounded-lg shadow max-w-md w-full">
            <div className="text-red-600 mb-2 text-lg font-semibold">⚠️ Erreur d'affichage</div>
            <div className="text-sm text-gray-600 mb-4">
              Une erreur s'est produite lors du chargement de {this.props.componentName || 'ce composant'}.
            </div>
            {this.state.error && (
              <details className="text-left text-xs text-gray-500 mb-4 p-2 bg-gray-50 rounded">
                <summary className="cursor-pointer font-medium mb-2">Détails de l'erreur</summary>
                <pre className="whitespace-pre-wrap overflow-auto">
                  {this.state.error.toString()}
                  {this.state.errorInfo && this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null, errorInfo: null });
                window.location.reload();
              }}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Recharger la page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;




