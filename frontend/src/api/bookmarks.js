import axios from 'axios'

let base = ''

export const bookmarksAdd = params => { return axios.post(`${base}/bookmarks/bookmarksAdd`, params).then(res => res.data) }
export const bookmarksEdit = params => { return axios.post(`${base}/bookmarks/bookmarksEdit`, params).then(res => res.data) }