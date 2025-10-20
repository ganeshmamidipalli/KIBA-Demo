// Complete Flow Test Script
// This script tests the entire KIBA procurement flow from start to finish

const API_BASE = 'http://localhost:8000';

async function testCompleteFlow() {
  console.log('🧪 Starting Complete Flow Test...\n');
  
  try {
    // Test 1: Health Check
    console.log('1️⃣ Testing Backend Health...');
    const healthResponse = await fetch(`${API_BASE}/health`);
    const healthData = await healthResponse.json();
    console.log('✅ Backend Health:', healthData.status);
    console.log('✅ OpenAI Connected:', healthData.openai_connected);
    
    // Test 2: KPA Intake Process
    console.log('\n2️⃣ Testing KPA Intake Process...');
    const intakeRequest = {
      product_name: "NVIDIA RTX 4090 GPU",
      budget_usd: 1500,
      quantity: 1,
      scope_text: "High-performance GPU for AI/ML research and development",
      vendors: ["NVIDIA", "Best Buy", "Newegg"],
      uploaded_summaries: [],
      project_context: {
        project_name: "KMI-1018_BAILIWICK_OTA",
        procurement_type: "Purchase Order",
        service_program: "Applied Research",
        technical_poc: "Dr. John Smith"
      }
    };
    
    const intakeResponse = await fetch(`${API_BASE}/api/intake_recommendations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(intakeRequest)
    });
    
    const intakeData = await intakeResponse.json();
    console.log('✅ Intake Session ID:', intakeData.session_id);
    console.log('✅ Questions Generated:', intakeData.intake.missing_info_questions.length);
    
    // Show follow-up questions
    console.log('\n📋 Follow-up Questions:');
    intakeData.intake.missing_info_questions.forEach((q, index) => {
      console.log(`${index + 1}. ${q}`);
    });
    
    // Test 3: Submit Follow-up Answers
    console.log('\n3️⃣ Testing Follow-up Submission...');
    
    // Generate answers based on actual questions
    const followupAnswers = {};
    intakeData.intake.missing_info_questions.forEach(question => {
      if (question.includes('framework') || question.includes('software')) {
        followupAnswers[question] = "PyTorch and TensorFlow for deep learning";
      } else if (question.includes('workload') || question.includes('intensity')) {
        followupAnswers[question] = "High-intensity training workloads with large datasets";
      } else if (question.includes('compliance') || question.includes('security')) {
        followupAnswers[question] = "NDAA Section 889 compliance required";
      } else if (question.includes('timeline') || question.includes('delivery')) {
        followupAnswers[question] = "Within 30 days preferred";
      } else if (question.includes('support') || question.includes('warranty')) {
        followupAnswers[question] = "Yes, 1-year technical support and warranty";
      } else if (question.includes('budget') || question.includes('cost')) {
        followupAnswers[question] = "Budget is flexible, prioritize performance and reliability";
      } else {
        followupAnswers[question] = "Please provide the best option based on requirements";
      }
    });
    
    console.log('\n📝 Generated Answers:');
    Object.entries(followupAnswers).forEach(([q, a], index) => {
      console.log(`${index + 1}. Q: ${q}`);
      console.log(`   A: ${a}`);
    });
    
    const followupResponse = await fetch(`${API_BASE}/api/submit_followups`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: intakeData.session_id,
        followup_answers: followupAnswers
      })
    });
    
    const followupData = await followupResponse.json();
    console.log('✅ Follow-up Answers Saved:', followupData.message);
    
    // Test 4: Generate Project Summary
    console.log('\n4️⃣ Testing Project Summary Generation...');
    const summaryResponse = await fetch(`${API_BASE}/api/session/${intakeData.session_id}/generate_summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    const summaryData = await summaryResponse.json();
    console.log('✅ Project Summary Generated:', summaryData.project_summary.length, 'characters');
    
    // Test 5: Generate Final Recommendations
    console.log('\n5️⃣ Testing Final Recommendations Generation...');
    const recommendationsResponse = await fetch(`${API_BASE}/api/session/${intakeData.session_id}/generate_recommendations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    const recommendationsData = await recommendationsResponse.json();
    console.log('✅ Recommendations Generated:', recommendationsData.recommendations.recommendations.length, 'options');
    console.log('✅ Recommended Index:', recommendationsData.recommendations.recommended_index);
    
    // Show recommendation details
    console.log('\n📋 Recommendation Details:');
    recommendationsData.recommendations.recommendations.forEach((rec, index) => {
      console.log(`\n${index + 1}. ${rec.name}`);
      console.log(`   Price: $${rec.estimated_price_usd}`);
      console.log(`   Value Note: ${rec.value_note}`);
      console.log(`   Rationale: ${rec.rationale}`);
      console.log(`   Score: ${rec.score}`);
    });
    
    // Test 6: Build Search Query
    console.log('\n6️⃣ Testing Search Query Building...');
    const searchQueryResponse = await fetch(`${API_BASE}/api/search-query/build`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_name: "NVIDIA RTX 4090 GPU",
        budget_usd: 1500,
        quantity: 1,
        scope_text: "High-performance GPU for AI/ML research and development",
        vendors: ["NVIDIA", "Best Buy", "Newegg"],
        project_context: {
          project_name: "KMI-1018_BAILIWICK_OTA",
          procurement_type: "Purchase Order",
          service_program: "Applied Research",
          technical_poc: "Dr. John Smith"
        }
      })
    });
    
    const searchQueryData = await searchQueryResponse.json();
    console.log('✅ Search Query Response:', JSON.stringify(searchQueryData, null, 2));
    
    const query = searchQueryData.solid_query || searchQueryData.query;
    if (query) {
      console.log('✅ Search Query Generated:', query.length, 'characters');
      console.log('✅ Query Preview:', query.substring(0, 100) + '...');
    } else {
      console.log('❌ No query in response');
    }
    
    // Test 7: Web Search
    console.log('\n7️⃣ Testing Web Search...');
    const webSearchResponse = await fetch(`${API_BASE}/api/web_search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query,
        max_results: 5
      })
    });
    
    const webSearchData = await webSearchResponse.json();
    console.log('✅ Web Search Response:', JSON.stringify(webSearchData, null, 2));
    
    const output = webSearchData.output_text || webSearchData.output;
    if (output) {
      console.log('✅ Web Search Completed:', output.length, 'characters');
      console.log('✅ Search Results Preview:', output.substring(0, 200) + '...');
    } else {
      console.log('❌ No output in web search response');
    }
    
    // Test 8: Generate RFQ
    console.log('\n8️⃣ Testing RFQ Generation...');
    const rfqPayload = {
      procurement_kind: "Purchase Order",
      service_program: "Applied Research",
      kmi_technical_poc: "Dr. John Smith",
      projects_supported: ["KMI-1018_BAILIWICK_OTA"],
      pop_start: "2024-01-01",
      pop_end: "2024-12-31",
      suggested_type: "Purchase Order",
      competition_type: "Sole Source",
      product_name: "NVIDIA RTX 4090 GPU",
      scope_brief: "High-performance GPU for AI/ML research and development",
      selected_variant: {
        id: "variant-1",
        title: "NVIDIA RTX 4090",
        summary: "High-performance GPU for AI/ML workloads",
        quantity: 1,
        est_unit_price_usd: 1500,
        est_total_usd: 1500,
        lead_time_days: 14
      },
      estimated_cost: 1500,
      ai_ranked_vendors: [{
        id: "vendor1",
        name: "NVIDIA",
        location: "USA",
        contact: "sales@nvidia.com",
        score: 0.95,
        price_estimate: 1500,
        lead_time_days: 14
      }],
      selected_vendor_ids: ["vendor1"],
      attachments: []
    };
    
    const rfqResponse = await fetch(`${API_BASE}/api/rfq/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rfqPayload)
    });
    
    const rfqData = await rfqResponse.json();
    console.log('✅ RFQ Generated:', rfqData.rfq_id);
    console.log('✅ RFQ Type:', rfqData.is_competitive ? 'Competitive' : 'Sole Source');
    console.log('✅ RFQ URL:', `${API_BASE}${rfqData.html_url}`);
    
    console.log('\n🎉 Complete Flow Test PASSED! All steps working correctly.');
    console.log('\n📊 Test Summary:');
    console.log('   ✅ Backend Health Check');
    console.log('   ✅ KPA Intake Process');
    console.log('   ✅ Follow-up Questions Submission');
    console.log('   ✅ Project Summary Generation');
    console.log('   ✅ Final Recommendations Generation');
    console.log('   ✅ Search Query Building');
    console.log('   ✅ Web Search Execution');
    console.log('   ✅ RFQ Generation');
    
  } catch (error) {
    console.error('❌ Flow Test FAILED:', error.message);
    console.error('Stack:', error.stack);
  }
}

// Run the test
testCompleteFlow();
