import { YantraCartridge, RenderOptions, RenderResult, YantraParameter } from './types';

export interface YantraEngineOptions {
    apiBase: string; // The URL of the Yantra API backend (e.g. http://localhost:5000)
}

/**
 * Headless SDK for rendering Yantra4D Cartridges.
 */
export class YantraEngine {
    private apiBase: string;

    constructor(options: YantraEngineOptions) {
        this.apiBase = options.apiBase;
    }

    /**
     * Evaluates the constraints of a cartridge and returns violations if any.
     * This logic is extracted from the React components for headless testing.
     */
    public evaluateConstraints(cartridge: YantraCartridge, params: Record<string, any>): Record<string, string[]> {
        const violations: Record<string, string[]> = {};
        const manifest = cartridge.manifest;

        for (const p of manifest.parameters) {
            if (p.min !== undefined && params[p.id] < p.min) {
                violations[p.id] = violations[p.id] || [];
                violations[p.id].push(`Value must be >= ${p.min}`);
            }
            if (p.max !== undefined && params[p.id] > p.max) {
                violations[p.id] = violations[p.id] || [];
                violations[p.id].push(`Value must be <= ${p.max}`);
            }
        }

        if (manifest.constraints) {
            for (const constraint of manifest.constraints) {
                try {
                    const result = this._evaluateRule(constraint.rule, params);
                    if (result === false) {
                        const affected = constraint.affects || this._extractParamIds(constraint.rule, manifest.parameters);
                        const msg = constraint.message?.en || constraint.rule;
                        for (const paramId of affected) {
                            violations[paramId] = violations[paramId] || [];
                            violations[paramId].push(msg);
                        }
                    }
                } catch {
                    // Skip malformed constraint expressions
                }
            }
        }

        return violations;
    }

    private _evaluateRule(rule: string, params: Record<string, any>): boolean {
        // Replace param names with values (longest-first to avoid partial matches)
        let expr = rule;
        const sortedKeys = Object.keys(params).sort((a, b) => b.length - a.length);
        for (const key of sortedKeys) {
            const val = params[key];
            const replacement = typeof val === 'string' ? `"${val}"` : String(val);
            expr = expr.replaceAll(key, replacement);
        }

        return this._safeEval(expr);
    }

    private _safeEval(expr: string): boolean {
        const cleaned = expr.trim();
        // Only allow digits, whitespace, decimal points, arithmetic, comparisons, boolean logic, quotes, and parens
        if (!/^[\d\s.+\-*/<>=!&|"'()]+$/.test(cleaned)) {
            throw new Error('Unsafe expression');
        }
        const fn = new Function(`"use strict"; return (${cleaned});`);
        return Boolean(fn());
    }

    private _extractParamIds(rule: string, parameters: YantraParameter[]): string[] {
        return parameters
            .filter(p => rule.includes(p.id))
            .map(p => p.id);
    }

    /**
     * Requests a backend render for the cartridge via the configured API.
     * Internally this constructs the same payload that the Studio frontend uses.
     */
    public async render(cartridge: YantraCartridge, options: RenderOptions): Promise<RenderResult> {
        const slug = cartridge.manifest.project.slug;
        const url = `${this.apiBase}/api/projects/${slug}/render`;

        const payload = {
            mode: options.mode,
            params: options.params || {},
            parts: options.parts || [],
            colors: options.colors || {}
        };

        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(`Render failed (${res.status}): ${errData.error || res.statusText}`);
        }

        const data = await res.json();
        return {
            url: `${this.apiBase}${data.url}`,
            logs: data.logs || ''
        };
    }

    /**
     * Retrieves default parameters for a cartridge
     */
    public getDefaultParams(cartridge: YantraCartridge): Record<string, any> {
        const params: Record<string, any> = {};
        for (const p of cartridge.manifest.parameters) {
            params[p.id] = p.default;
        }
        return params;
    }
}
