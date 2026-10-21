// @vitest-environment node
/**
 * geom-core differential suite under Vitest's Node environment.
 * Twin: geomCore.differential.jsdom.test.js (the Studio's default environment).
 */
import { defineGeomCoreDifferentialSuite } from './__fixtures__/geomCoreDifferentialSuite'

defineGeomCoreDifferentialSuite('node')
