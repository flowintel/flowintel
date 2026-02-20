import {display_toast} from '../toaster.js'
import {message_list} from '/static/js/toaster.js'
import {getTextColor, mapIcon} from '/static/js/utils.js'
const { ref, nextTick, onMounted, watch } = Vue
export default {
    delimiters: ['[[', ']]'],
    props:{type_object: String},
	emits: ['st', 'sc', 'sct', 'sg', "delete_st", "delete_sc", "delete_sg", "delete_sct"],
	setup(props, {emit}) {
		const taxonomies = ref([])
        const galaxies = ref([])
        const tags_list = ref([])
        const cluster_list = ref([])
        const custom_tags = ref([])

        const selected_taxo = ref([])
        const selected_tags = ref([])
        const selected_galaxies = ref([])
        const selected_clusters = ref([])
        const selected_custom_tags = ref([])


        async function fetch_taxonomies(){
            const res = await fetch("/case/get_taxonomies")
            if(await res.status==400 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                taxonomies.value = loc["taxonomies"]
            }
        }fetch_taxonomies()

        async function fetch_galaxies(){
            const res = await fetch("/case/get_galaxies")
            if(await res.status==400 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                galaxies.value = loc["galaxies"]
            }
        }fetch_galaxies()

        async function fetch_tags(s_taxo){
            tags_list.value = []
            const res = await fetch("/case/get_tags?taxonomies=" + JSON.stringify(s_taxo))
            if(await res.status==400 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                tags_list.value = loc["tags"]

                await nextTick()
                $('#tags_select').trigger('change');
            }
        }

        async function fetch_cluster(s_galaxies){
            cluster_list.value = []
            const res = await fetch("/case/get_clusters?galaxies=" + JSON.stringify(s_galaxies))
            if(await res.status==400 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                cluster_list.value = loc["clusters"]
                
                await nextTick()
                $('#clusters_select').change();
            }
        }

        async function fetch_custom_tags(){
            const res = await fetch("/custom_tags/list")
            if(await res.status==400 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                custom_tags.value = loc
            }
        }fetch_custom_tags()
        

        async function fetch_taxonomies_case_task(){
            let url

            if(props.type_object == "case"){
                url = "/case/get_taxonomies_case/" +window.location.pathname.split("/").slice(-1)
            }
            else if(props.type_object == "task"){
                url = "/case/get_taxonomies_task/" +window.location.pathname.split("/").slice(-1)
            }
            else if(props.type_object == "case_template"){
                url = "/templating/get_taxonomies_case/" +window.location.pathname.split("/").slice(-1)
            }
            else if(props.type_object == "task_template"){
                url = "/templating/get_taxonomies_task/" +window.location.pathname.split("/").slice(-1)
            }

            const res = await fetch(url)
            if(await res.status==400 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                selected_tags.value = loc["tags"]
                selected_taxo.value = loc["taxonomies"]
                
                emit('st', loc["tags"])
            }
            
            if(selected_taxo.value.length > 0){
                let loc_list_name = []
                $.each(selected_taxo.value, function (index, value) {
                    loc_list_name.push(value)
                });
                fetch_tags(loc_list_name)
            }
        }
        fetch_taxonomies_case_task()

        async function fetch_galaxies_case_task(){
            let url 
            if(props.type_object == "case"){
                url = "/case/get_galaxies_case/" +window.location.pathname.split("/").slice(-1)
            }
            else if(props.type_object == "task"){
                url = "/case/get_galaxies_task/" +window.location.pathname.split("/").slice(-1)
            }
            else if(props.type_object == "case_template"){
                url = "/templating/get_galaxies_case/" +window.location.pathname.split("/").slice(-1)
            }
            else if(props.type_object == "task_template"){
                url = "/templating/get_galaxies_task/" +window.location.pathname.split("/").slice(-1)
            }

            const res = await fetch(url)
            if(await res.status==400 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                selected_clusters.value = loc["clusters"]
                selected_galaxies.value = loc["galaxies"]
                emit('sc', loc["clusters"])
                emit('sg', loc["galaxies"])
            }
            if(selected_galaxies.value.length > 0){
                let loc_list_name = []
                $.each(selected_galaxies.value, function (index, value) {
                    loc_list_name.push(value.name)
                });
                
                fetch_cluster(loc_list_name)
            }
        }
        fetch_galaxies_case_task()

        async function fetch_custom_tags_case_task(){
            let url

            if(props.type_object == "case"){
                url = "/case/get_custom_tags_case/" +window.location.pathname.split("/").slice(-1)
            }
            else if(props.type_object == "task"){
                url = "/case/get_custom_tags_task/" +window.location.pathname.split("/").slice(-1)
            }
            else if(props.type_object == "case_template"){
                url = "/templating/get_custom_tags_case/" +window.location.pathname.split("/").slice(-1)
            }
            else if(props.type_object == "task_template"){
                url = "/templating/get_custom_tags_task/" +window.location.pathname.split("/").slice(-1)
            }

            const res = await fetch(url)
            if(await res.status==400 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                selected_custom_tags.value = loc["custom_tags"]
                emit('sct', loc["custom_tags"])
            }
        }
        fetch_custom_tags_case_task()


        function delete_galaxy_select(galax_uuid){
            let loc
            for(let i in selected_galaxies.value){
                if(galax_uuid == selected_galaxies.value[i].uuid){
                    loc = i
                    break
                }
            }
            selected_galaxies.value.splice(loc, 1)
            emit("delete_sg", loc)

            let loc_list_name = []
            $.each(selected_galaxies.value, function (index, value) {
                loc_list_name.push(value.name)
            });
            fetch_cluster(loc_list_name)
        }
        function delete_cluster_select(cluster_uuid){
            let loc
            for(let i in selected_clusters.value){
                if(cluster_uuid == selected_clusters.value[i].uuid){
                    loc = i
                    break
                }
            }
            selected_clusters.value.splice(loc, 1)
            emit("delete_sc", loc)
        }

        function delete_taxo_select(taxo_name){
            let loc
            for(let i in selected_taxo.value){
                if(taxo_name == selected_taxo.value[i].uuid){
                    loc = i
                    break
                }
            }
            selected_taxo.value.splice(loc, 1)

            let loc_list_name = []
            $.each(selected_taxo.value, function (index, value) {
                loc_list_name.push(value.name)
            });
            fetch_tags(loc_list_name)
        }

        function delete_tag_select(tag_name){
            let loc
            for(let i in selected_tags.value){
                if(tag_name == selected_tags.value[i].name){
                    loc = i
                    break
                }
            }
            selected_tags.value.splice(loc, 1)
            emit("delete_st", loc)
        }

        function delete_custom_tag_select(custom_tag){
            let loc
            for(let i in selected_custom_tags.value){
                if(custom_tag == selected_custom_tags.value[i].name){
                    loc = i
                    break
                }
            }
            selected_custom_tags.value.splice(loc, 1)
            emit("delete_sct", loc)
        }
        
        // Disable already-selected options in dropdowns
        function updateTagsDropdown() {
            const selected_names = selected_tags.value.map(tag => tag.name)
            $('#tags_select option').each(function() {
                const $option = $(this)
                $option.prop('disabled', selected_names.includes($option.val()))
            })
        }

        function updateClustersDropdown() {
            const selected_uuids = selected_clusters.value.map(cluster => cluster.uuid)
            $('#clusters_select option').each(function() {
                const $option = $(this)
                $option.prop('disabled', selected_uuids.includes($option.val()))
            })
        }

        function updateGalaxiesDropdown() {
            const selected_names = selected_galaxies.value.map(galaxy => galaxy.name)
            $('#galaxies_select option').each(function() {
                const $option = $(this)
                $option.prop('disabled', selected_names.includes($option.val()))
            })
        }

        function updateCustomTagsDropdown() {
            const selected_names = selected_custom_tags.value.map(tag => tag.name)
            $('#custom_select option').each(function() {
                const $option = $(this)
                $option.prop('disabled', selected_names.includes($option.val()))
            })
        }

        // Watch for changes in selected items and update dropdowns
        watch(selected_tags, () => {
            nextTick(() => updateTagsDropdown())
        }, { deep: true })

        watch(selected_clusters, () => {
            nextTick(() => updateClustersDropdown())
        }, { deep: true })

        watch(selected_galaxies, () => {
            nextTick(() => updateGalaxiesDropdown())
        }, { deep: true })

        watch(selected_custom_tags, () => {
            nextTick(() => updateCustomTagsDropdown())
        }, { deep: true })

        watch(tags_list, () => {
            nextTick(() => updateTagsDropdown())
        }, { deep: true })

        watch(cluster_list, () => {
            nextTick(() => updateClustersDropdown())
        }, { deep: true })
        
        watch(custom_tags, () => {
            nextTick(() => updateCustomTagsDropdown())
        }, { deep: true })
        

        onMounted(() => {
            $('.select2-select').select2({
                theme: 'bootstrap-5',
                closeOnSelect: false
            })

            $('#taxonomies_select').on('select2:select', function (e) {
                let loc_name = $(this).select2('data').map(item => item.id)                    
                
                if(!selected_taxo.value.includes(loc_name[0]) ){
                    selected_taxo.value.push(loc_name[0])

                    let loc_list_name = []
                    $.each(selected_taxo.value, function (index, value) {                        
                        loc_list_name.push(value)
                    });
                    fetch_tags(loc_list_name)
                }
                $('#taxonomies_select').val('').change()
            })

            $('#tags_select').on('select2:select', function (e) {
                let loc_name = $(this).select2('data').map(item => item.id)
                let flag = false
                
                for(let i in selected_tags.value){
                    if(selected_tags.value[i].name == loc_name[0]){
                        flag = true
                        break
                    }
                }
                if(!flag){
                    for( let c in tags_list.value){
                        for (let k in tags_list.value[c]){
                            if(tags_list.value[c][k].name == loc_name[0]){
                                selected_tags.value.push(tags_list.value[c][k])
                                emit("st", tags_list.value[c][k])
                                break
                            }
                        }
                    }
                }
                
                $('#tags_select').val('').change()
            })

            $('#galaxies_select').on('select2:select', function (e) {
                let loc_name = $(this).select2('data').map(item => item.id)                    
                
                for( let c in galaxies.value){
                    if(galaxies.value[c].name == loc_name){
                        if(!selected_galaxies.value.includes(galaxies.value[c]) ){
                            selected_galaxies.value.push(galaxies.value[c])
                            emit("sg", galaxies.value[c])
                            break
                        }
                    }
                }
                let loc_list_name = []
                $.each(selected_galaxies.value, function (index, value) {
                    loc_list_name.push(value.name)
                });
                fetch_cluster(loc_list_name)

                $('#galaxies_select').val('').change()
            })

            $('#clusters_select').on('select2:select', function (e) {
                let loc_uuid = $(this).select2('data').map(item => item.id)
                
                for( let c in cluster_list.value){
                    for (let k in cluster_list.value[c]){
                        if(cluster_list.value[c][k].uuid == loc_uuid){
                            if(!selected_clusters.value.includes(cluster_list.value[c][k]) ){
                                selected_clusters.value.push(cluster_list.value[c][k])
                                emit("sc", cluster_list.value[c][k])
                                break
                            }
                        }
                    }
                }
                $('#clusters_select').val('').change()
            })

            $('#custom_select').on('select2:select', function (e) {
                let loc_name = $(this).select2('data').map(item => item.id)

                for( let c in custom_tags.value){
                    if(custom_tags.value[c].name == loc_name){
                        if(!selected_custom_tags.value.includes(custom_tags.value[c]) ){
                            selected_custom_tags.value.push(custom_tags.value[c])                            
                            emit("sct", custom_tags.value[c])
                            break
                        }
                    }
                }
                
                $('#custom_select').val('').change()
            })
        })

		return {
            message_list,
            getTextColor,
            mapIcon,

            taxonomies,
            galaxies,
            tags_list,
            cluster_list,
            custom_tags,

            selected_taxo,
            selected_tags,
            selected_galaxies,
            selected_clusters,
            selected_custom_tags,

            delete_galaxy_select,
            delete_cluster_select,
            delete_taxo_select,
            delete_tag_select,
            delete_custom_tag_select
		}
    },
	template: `
    <div class="row">
        <div v-if="custom_tags" class="col-6">
            <h5>Custom Tags</h5>
            <select data-placeholder="Custom Tags" class="select2-select form-control" multiple id="custom_select" >
                <template v-for="c_t in custom_tags">
                    <option :value="[[c_t.name]]">[[c_t.name]]</option>
                </template>
            </select>
        </div>
        <div class="col-6 card">
            <b>Selected Custom Tags</b>
            <table class="table">
                <tbody>
                    <tr v-for="custom_tag in selected_custom_tags">
                        <td>
                            <div class="tag" :style="{'background-color':custom_tag.color, 'color': getTextColor(custom_tag.color)}">
                                <i :class="[[custom_tag.icon]]"></i> [[custom_tag.name]]
                            </div>
                        </td> 
                        <td>
                            <button type="button" class="btn btn-outline-danger btn-sm" @click="delete_custom_tag_select(custom_tag.name)">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td> 
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    <hr>

    <h5>Taxonomies:</h5>
    <div class="row">
        <div class="col-6">
            <template v-if="taxonomies">
                <select data-placeholder="Taxonomies" class="select2-select form-control" multiple name="taxonomies_select" id="taxonomies_select" >
                    <template v-for="taxonomy in taxonomies">
                        <option :value="[[taxonomy]]">[[taxonomy]]</option>
                    </template>
                </select>
            </template>
        </div>
        
        <div class="col-6">
            <template v-if="tags_list">
                <select data-placeholder="Tags" class="select2-select form-control" multiple id="tags_select" >
                    <template v-for="(tags, taxo) in tags_list">
                        <optgroup :label="[[taxo]]">
                            <template v-for="tag in tags">
                                <option :value="[[tag.name]]" :title="tag.description">[[tag.name]]</option>
                            </template>
                        </optgroup>
                    </template>
                </select>
            </template>
        </div>
    </div>
    <div class="row p-2">
        <div class="col-6 card" >
            <b>Selected Taxonomies</b>
            <table class="table">
                <tbody>
                    <tr v-for="taxo in selected_taxo">
                        <td>[[taxo]]</td> 
                        <td>
                            <button type="button" class="btn btn-outline-danger btn-sm" @click="delete_taxo_select(taxo.uuid)">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td> 
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="col-6 card">
            <b>Selected Tags</b>
            <table class="table" v-if="selected_tags.length">
                <tbody>
                    <tr v-for="tag in selected_tags">
                        <td> 
                            <div class="tag" :style="{'background-color':tag.color, 'color': getTextColor(tag.color)}">
                                <i class="fa-solid fa-tag" style="margin-right: 3px; margin-left: 3px;"></i>[[tag.name]]
                            </div>
                        </td>
                        <td>
                            <button type="button" class="btn btn-outline-danger btn-sm" @click="delete_tag_select(tag.name)">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td> 
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    <hr>

    <h5>Galaxies:</h5>
    <div class="row">
        <div class="col-6">
            <template v-if="galaxies">
                <select data-placeholder="Galaxies" class="select2-select form-control" multiple name="galaxies_select" id="galaxies_select" >
                    <template v-for="galaxy, key in galaxies">
                        <option :value="[[galaxy.name]]">[[galaxy.name]]</option>
                    </template>
                </select>
            </template>
        </div>
        
        <div class="col-6">
            <template v-if="cluster_list">
                <select data-placeholder="Cluster" class="select2-select form-control" multiple id="clusters_select" >
                    <template v-for="(clusters, galaxy) in cluster_list">
                        <optgroup :label="[[galaxy]]">
                            <template v-for="cluster in clusters">
                                <option :value="[[cluster.uuid]]" :title="cluster.description">[[cluster.tag]]</option>
                            </template>
                        </optgroup>
                    </template>
                </select>
            </template>
        </div>
    </div>
    <div class="row p-2">
        <div class="col-6 card" >
            <b>Selected Galaxies</b>
            <table class="table" >
                <tbody>
                    <tr v-for="galax in selected_galaxies">
                        <td>[[galax.name]]</td> 
                        <td>
                            <button type="button" class="btn btn-outline-danger btn-sm" @click="delete_galaxy_select(galax.uuid)">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td> 
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="col-6 card">
            <b>Selected Clusters</b>
            <table class="table">
                <tbody>
                    <tr v-for="clus in selected_clusters">
                        <td>
                            <span class="cluster">
                                <span v-html="mapIcon(clus.icon)"></span>
                                [[clus.tag]]
                            </span>
                        </td>
                        <td>
                            <button type="button" class="btn btn-outline-danger btn-sm" @click="delete_cluster_select(clus.uuid)">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td> 
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    `
}