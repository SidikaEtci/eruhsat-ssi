/**
 * Shared municipality settings for the Turkey e-license platform.
 */
const CitySettings = (() => {
    const STORAGE_KEY = 'selected_city_slug';
    let settings = null;
    let currentCity = null;

    async function load() {
        if (settings) {
            return settings;
        }
        const response = await fetch('/api/settings');
        settings = await response.json();
        const saved = localStorage.getItem(STORAGE_KEY);
        const slug = saved || settings.default_city_slug;
        currentCity = settings.cities.find((c) => c.slug === slug) || settings.city;
        return settings;
    }

    function getSelectedCity() {
        return currentCity;
    }

    function getSelectedSlug() {
        return currentCity?.slug || settings?.default_city_slug || 'konya';
    }

    function setSelectedCity(slug) {
        const city = settings.cities.find((c) => c.slug === slug);
        if (!city) {
            return;
        }
        currentCity = city;
        localStorage.setItem(STORAGE_KEY, slug);
        applyBranding();
        populateDistrictSelect();
        updateLicensePlaceholders();
    }

    function applyBranding() {
        if (!currentCity) {
            return;
        }
        const title = `${currentCity.name} E-License`;
        document.title = title;

        document.querySelectorAll('[data-city-title]').forEach((el) => {
            el.textContent = title;
        });
        document.querySelectorAll('[data-city-subtitle]').forEach((el) => {
            el.textContent = `${currentCity.name} — Blockchain-Based Digital License Management`;
        });
        document.querySelectorAll('[data-issuer-name]').forEach((el) => {
            const city = settings.cities.find((c) => c.slug === getSelectedSlug());
            if (city) {
                el.textContent = city.name;
            }
        });
    }

    function populateCitySelect(selectId = 'citySelect') {
        const select = document.getElementById(selectId);
        if (!select || !settings) {
            return;
        }
        select.innerHTML = settings.cities
            .map(
                (city) =>
                    `<option value="${city.slug}" ${city.slug === getSelectedSlug() ? 'selected' : ''}>${city.name}</option>`
            )
            .join('');
        select.onchange = () => {
            setSelectedCity(select.value);
            document.dispatchEvent(new CustomEvent('city-changed', { detail: getSelectedCity() }));
        };
    }

    function populateDistrictSelect(selectId = 'regionSelect') {
        const select = document.getElementById(selectId);
        if (!select || !currentCity) {
            return;
        }
        select.innerHTML =
            '<option value="">Select...</option>' +
            currentCity.districts.map((d) => `<option value="${d}">${d}</option>`).join('');
    }

    function updateLicensePlaceholders() {
        if (!currentCity) {
            return;
        }
        const example = currentCity.license_id_example;
        document.querySelectorAll('[data-license-placeholder]').forEach((el) => {
            el.placeholder = `e.g. ${example}`;
        });
        const hidden = document.getElementById('issueCitySlug');
        if (hidden) {
            hidden.value = currentCity.slug;
        }
    }

    function apiQuery() {
        return `city=${encodeURIComponent(getSelectedSlug())}`;
    }

    async function init(options = {}) {
        await load();
        applyBranding();
        if (options.citySelectId !== false) {
            populateCitySelect(options.citySelectId || 'citySelect');
        }
        populateDistrictSelect(options.districtSelectId || 'regionSelect');
        updateLicensePlaceholders();
        return settings;
    }

    return {
        init,
        load,
        getSelectedCity,
        getSelectedSlug,
        setSelectedCity,
        apiQuery,
        applyBranding,
    };
})();
