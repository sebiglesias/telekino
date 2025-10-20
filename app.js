class TelekinoApp {
    constructor() {
        this.sorteos = {};
        this.sorteoActual = null;
        this.sorteosDisponibles = [];
        this.init();
    }

    async init() {
        await this.loadData();
        this.renderSorteoActual();
        this.setupEventListeners();
    }

    async loadData() {
        try {
            // Cargar datos reales del scraper
            const response = await fetch('telekino-data/resultados.json');
            const data = await response.json();

            console.log('Datos cargados:', data);

            // Cargar todos los sorteos en un objeto único
            this.sorteos = {};

            // Agregar sorteo actual
            if (data.current_draw) {
                this.sorteoActual = data.current_draw;
                this.sorteos[data.current_draw.numero_sorteo] = data.current_draw;
            }

            // Agregar sorteos históricos
            if (data.historical_draws) {
                Object.keys(data.historical_draws).forEach(numero => {
                    this.sorteos[numero] = data.historical_draws[numero];
                });
            }

            this.sorteosDisponibles = data.available_draws || [];

            console.log('Sorteos cargados:', Object.keys(this.sorteos).length);
            console.log('Sorteos disponibles:', this.sorteosDisponibles.length);

        } catch (error) {
            console.error('Error cargando datos:', error);
            this.showError('Error cargando los resultados. Ejecuta el scraper primero.');
        }
    }

    renderSorteoActual() {
        if (!this.sorteoActual) {
            this.showError('No hay datos del sorteo actual. Ejecuta el scraper primero.');
            return;
        }

        this.renderNumerosTelekino(this.sorteoActual);
        this.renderNumerosRekino(this.sorteoActual);
        this.renderInfoSorteo(this.sorteoActual);
        this.renderSorteosDisponibles();
    }

    renderNumerosTelekino(drawData) {
        const container = document.getElementById('telekino-numbers');
        if (!container) return;

        if (!drawData.numeros_telekino || drawData.numeros_telekino.length === 0) {
            container.innerHTML = '<div class="no-data">No hay números de Telekino disponibles</div>';
            return;
        }

        container.innerHTML = drawData.numeros_telekino.map(num => `
            <div class="number">${num.toString().padStart(2, '0')}</div>
        `).join('');
    }

    renderNumerosRekino(drawData) {
        const container = document.getElementById('rekino-numbers');
        if (!container) return;

        if (!drawData.numeros_rekino || drawData.numeros_rekino.length === 0) {
            container.innerHTML = '<div class="no-data">No hay números de Rekino disponibles</div>';
            return;
        }

        container.innerHTML = drawData.numeros_rekino.map(num => `
            <div class="number rekino">${num.toString().padStart(2, '0')}</div>
        `).join('');
    }

    renderInfoSorteo(drawData) {
        // Actualizar información básica del sorteo
        if (drawData.numero_sorteo) {
            const elem = document.getElementById('draw-number');
            if (elem) elem.textContent = `Sorteo #${drawData.numero_sorteo}`;
        }

        if (drawData.fecha) {
            const elem = document.getElementById('draw-date');
            if (elem) elem.textContent = this.formatDate(drawData.fecha);
        }
    }

    renderSorteosDisponibles() {
        const container = document.getElementById('available-draws');
        if (!container) return;

        if (this.sorteosDisponibles.length === 0) {
            container.innerHTML = '<option value="">No hay sorteos disponibles</option>';
            return;
        }

        container.innerHTML = this.sorteosDisponibles.map(draw => `
            <option value="${draw.numero}" ${draw.numero === this.sorteoActual.numero_sorteo ? 'selected' : ''}>
                Sorteo ${draw.numero} - ${draw.fecha} - ${draw.color}
            </option>
        `).join('');
    }

    setupEventListeners() {
        // Selector de sorteos
        const selectDraw = document.getElementById('available-draws');
        if (selectDraw) {
            selectDraw.addEventListener('change', (e) => {
                const selectedSorteo = e.target.value;
                this.onDrawChange(selectedSorteo);
            });
        }
    }

    async onDrawChange(sorteoNumero) {
        console.log('Sorteo seleccionado:', sorteoNumero);

        if (!sorteoNumero) return;

        // Mostrar loading inmediatamente
        this.showLoadingMessage();

        // Pequeño delay para mejor UX
        await new Promise(resolve => setTimeout(resolve, 300));

        const drawData = this.sorteos[sorteoNumero];

        if (drawData) {
            console.log('Datos del sorteo encontrados:', drawData);
            this.updateDrawView(drawData);
        } else {
            console.log('No hay datos para el sorteo:', sorteoNumero);
            this.showNoDataMessage(sorteoNumero);
        }
    }

    updateDrawView(drawData) {
        // Actualizar información del sorteo
        this.renderInfoSorteo(drawData);

        // Actualizar números
        this.renderNumerosTelekino(drawData);
        this.renderNumerosRekino(drawData);

        // Mostrar información adicional si está disponible
        this.showAdditionalInfo(drawData);
    }

    showAdditionalInfo(drawData) {
        // Aquí puedes agregar información adicional como premios, etc.
        if (drawData.premios && Object.keys(drawData.premios).length > 0) {
            console.log('Premios disponibles:', drawData.premios);
        }
    }

    showLoadingMessage() {
        const telekinoContainer = document.getElementById('telekino-numbers');
        const rekinoContainer = document.getElementById('rekino-numbers');

        if (telekinoContainer) {
            telekinoContainer.innerHTML = '<div class="loading">Cargando números Telekino...</div>';
        }
        if (rekinoContainer) {
            rekinoContainer.innerHTML = '<div class="loading">Cargando números Rekino...</div>';
        }
    }

    showNoDataMessage(sorteoNumero) {
        const telekinoContainer = document.getElementById('telekino-numbers');
        const rekinoContainer = document.getElementById('rekino-numbers');

        const message = `
            <div class="no-data">
                <i class="fas fa-exclamation-triangle"></i>
                <p>No hay datos disponibles para el sorteo ${sorteoNumero}</p>
                <small>El scraper no pudo obtener los números de este sorteo histórico</small>
            </div>
        `;

        if (telekinoContainer) telekinoContainer.innerHTML = message;
        if (rekinoContainer) rekinoContainer.innerHTML = message;

        // Mantener la información del sorteo aunque no tengamos números
        const drawNumberElem = document.getElementById('draw-number');
        const drawDateElem = document.getElementById('draw-date');

        if (drawNumberElem) drawNumberElem.textContent = `Sorteo #${sorteoNumero}`;
        if (drawDateElem) drawDateElem.textContent = 'Fecha no disponible';
    }

    formatDate(dateString) {
        try {
            if (dateString.includes('/')) {
                const [day, month, year] = dateString.split('/');
                const fullYear = year.length === 2 ? `20${year}` : year;
                return new Date(`${fullYear}-${month}-${day}`).toLocaleDateString('es-AR', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
            } else if (dateString.includes('-')) {
                const [day, month, year] = dateString.split('-');
                const fullYear = year.length === 2 ? `20${year}` : year;
                return new Date(`${fullYear}-${month}-${day}`).toLocaleDateString('es-AR', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
            }
            return dateString;
        } catch (e) {
            return dateString;
        }
    }

    showError(message) {
        const container = document.querySelector('main');
        if (container) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.innerHTML = `
                <i class="fas fa-exclamation-circle"></i>
                ${message}
            `;
            container.prepend(errorDiv);
        }
    }
}

// Inicializar la aplicación cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    new TelekinoApp();
});