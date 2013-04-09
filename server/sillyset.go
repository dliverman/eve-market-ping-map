package main

type SystemIdSet struct {
	set            map[int64]bool
	SystemsPresent bool
}

func NewSystemIdSet() *SystemIdSet {
	return &SystemIdSet{
		set:            make(map[int64]bool),
		SystemsPresent: false,
	}
}

func (set *SystemIdSet) AddSysId(id int64) {
	set.set[id] = true
	set.SystemsPresent = true
}

func (set *SystemIdSet) GetList() *[]int64 {
	var sysIds []int64
	for sysId, _ := range set.set {
		sysIds = append(sysIds, sysId)
	}
	return &sysIds
}
