import timeline_graph from './timeline_graph.js'

// Flowtime supplies the view slot and lifecycle. Vue, Pivotick and graph data stay here.
export function createFlowtimeGraphView({ caseId, getCasesInfo, onEventsChanged }) {
    return {
        id: 'graph',
        label: 'Graph',
        icon: '⌘',
        filters: false,
        inspector: false,
        mount(container) {
            const app = Vue.createApp({
                render: () => Vue.h(timeline_graph, {
                    case_id: caseId,
                    cases_info: getCasesInfo(),
                    onEventsChanged
                })
            })
            app.mount(container)
            return { destroy: () => app.unmount() }
        }
    }
}
